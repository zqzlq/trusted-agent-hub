/**
 * Deterministic installed-content digest (`sha256-tree-v1`).
 *
 * Produces a stable SHA-256 hash of a directory tree that is:
 *   - Independent of creation order (files/dirs are sorted)
 *   - Sensitive to content changes, additions, deletions, and renames
 *   - Resistant to symlink/junction/device tricks
 *
 * Algorithm (`sha256-tree-v1`):
 *   root must be a plain directory (not a symlink / reparse point)
 *   recurse with lstat — never follow symlinks
 *   relative paths are POSIX-normalised ("/") and sorted with locale-independent
 *     binary comparison
 *   each directory  → `D\0<relative-path>\0`
 *   each file       → `F\0<relative-path>\0<size>\0` + raw bytes + `\0`
 *   files are opened, fstat'd after open, then read in chunks with real-time
 *     byte enforcement (no single 500 MiB allocation)
 *   symlink, junction, socket, FIFO, device → rejected
 *   digest is the 64-char lowercase hex SHA-256 of the concatenated input
 */

import * as crypto from 'crypto';
import * as fs from 'fs';
import * as path from 'path';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const CONTENT_HASH_ALGORITHM = 'sha256-tree-v1' as const;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DirectoryDigest {
  algorithm: typeof CONTENT_HASH_ALGORITHM;
  digest: string;       // 64-char lowercase hex
  fileCount: number;
  totalBytes: number;
}

export interface DigestLimits {
  maxFiles?: number;    // default 10000
  maxBytes?: number;    // default 500 MiB
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

export class ContentIntegrityError extends Error {
  constructor(
    message: string,
    public code: string,
  ) {
    super(message);
    this.name = 'ContentIntegrityError';
  }
}

// ---------------------------------------------------------------------------
// Default limits
// ---------------------------------------------------------------------------

const DEFAULT_MAX_FILES = 10_000;
const DEFAULT_MAX_BYTES = 500 * 1024 * 1024; // 500 MiB
const CHUNK_SIZE = 64 * 1024; // 64 KiB

// ---------------------------------------------------------------------------
// Locale-independent string comparison
// ---------------------------------------------------------------------------

/**
 * Compare two strings using binary UTF-16 code-unit order.
 * Unlike `localeCompare`, this produces the same ordering on every platform
 * regardless of the system locale.
 */
function binaryCompare(a: string, b: string): number {
  if (a < b) return -1;
  if (a > b) return 1;
  return 0;
}

// ---------------------------------------------------------------------------
// Ancestor chain validation
// ---------------------------------------------------------------------------

/**
 * Verify that every path component from the filesystem root down to `target`
 * is a real directory — not a symlink, junction, or reparse point.
 *
 * This prevents junction-based escapes where an ancestor directory redirects
 * the lexical path to a physically different location on disk.
 */
export function validateAncestorChain(target: string): void {
  const resolved = path.resolve(target);

  // Use path.parse to get the filesystem root (e.g. "/" on Linux, "C:\" on
  // Windows, "\\server\share\" for UNC).  Starting from the root avoids the
  // bug where splitting an absolute POSIX path loses the leading separator
  // and path.resolve() rebuilds relative to cwd.
  const root = path.parse(resolved).root;
  if (!root) {
    throw new ContentIntegrityError(
      `Cannot determine filesystem root for "${resolved}"`,
      'unsafe_content',
    );
  }

  // Build the relative segments from root to resolved
  const relative = path.relative(root, resolved);
  if (!relative) {
    // resolved is the root itself — stat it directly
    let stat: fs.Stats;
    try {
      stat = fs.lstatSync(root);
    } catch (err: unknown) {
      throw new ContentIntegrityError(
        `Cannot stat root "${root}": ${err instanceof Error ? err.message : String(err)}`,
        'unsafe_content',
      );
    }
    if (stat.isSymbolicLink()) {
      throw new ContentIntegrityError(
        `Filesystem root "${root}" is a symbolic link`,
        'unsafe_content',
      );
    }
    if (!stat.isDirectory()) {
      throw new ContentIntegrityError(
        `Filesystem root "${root}" is not a directory`,
        'unsafe_content',
      );
    }
    return;
  }

  const parts = relative.split(path.sep).filter(Boolean);

  let current = root;
  // Validate the root itself first
  {
    let stat: fs.Stats;
    try {
      stat = fs.lstatSync(current);
    } catch (err: unknown) {
      throw new ContentIntegrityError(
        `Cannot stat root "${current}": ${err instanceof Error ? err.message : String(err)}`,
        'unsafe_content',
      );
    }
    if (stat.isSymbolicLink()) {
      throw new ContentIntegrityError(
        `Root path "${current}" is a symbolic link — must be a real directory`,
        'unsafe_content',
      );
    }
    if (!stat.isDirectory()) {
      throw new ContentIntegrityError(
        `Root path "${current}" is not a directory`,
        'unsafe_content',
      );
    }
  }

  for (const part of parts) {
    current = path.join(current, part);

    let stat: fs.Stats;
    try {
      stat = fs.lstatSync(current);
    } catch (err: unknown) {
      throw new ContentIntegrityError(
        `Cannot stat ancestor "${current}": ${err instanceof Error ? err.message : String(err)}`,
        'unsafe_content',
      );
    }

    if (stat.isSymbolicLink()) {
      throw new ContentIntegrityError(
        `Ancestor path "${current}" is a symbolic link — must be a real directory`,
        'unsafe_content',
      );
    }

    // On Windows, junctions are reported as directories by Node but we can
    // detect reparse points via the birthtime/file attribute pattern.
    // The most reliable cross-platform check: if it's not a directory (after
    // symlink check), reject.
    if (!stat.isDirectory()) {
      throw new ContentIntegrityError(
        `Ancestor path "${current}" is not a directory`,
        'unsafe_content',
      );
    }
  }
}

// ---------------------------------------------------------------------------
// Implementation
// ---------------------------------------------------------------------------

interface FileIdentity {
  dev: bigint;
  ino: bigint;
  size: bigint;
}

interface FileEntry {
  relPath: string;
  size: number;
  absPath: string;
  /** Identity from initial lstat — compared after open to detect TOCTOU swap */
  identity: FileIdentity;
}

interface DirEntry {
  relPath: string;
  absPath: string;
}

/**
 * Collect every filesystem entry under `root`, validating and computing a
 * stable, ordered representation.  No file content is read here — only
 * metadata (lstat).
 */
async function collectEntries(
  root: string,
  limits: Required<DigestLimits>,
): Promise<{ dirs: DirEntry[]; files: FileEntry[] }> {
  const dirs: DirEntry[] = [];
  const files: FileEntry[] = [];
  let fileCount = 0;
  let totalBytes = 0;

  async function walk(currentDir: string, relPrefix: string): Promise<void> {
    let dirEntries: fs.Dirent[];
    try {
      dirEntries = fs.readdirSync(currentDir, { withFileTypes: true });
    } catch (err: unknown) {
      throw new ContentIntegrityError(
        `Cannot read directory "${currentDir}": ${err instanceof Error ? err.message : String(err)}`,
        'read_error',
      );
    }

    // Sort entries with locale-independent binary comparison
    dirEntries.sort((a, b) => binaryCompare(a.name, b.name));

    for (const entry of dirEntries) {
      const absPath = path.join(currentDir, entry.name);
      const relPath = relPrefix ? `${relPrefix}/${entry.name}` : entry.name;

      // Use lstat with bigint to avoid following symlinks and preserve full
      // inode precision for identity comparison (inode numbers can exceed
      // Number.MAX_SAFE_INTEGER on some filesystems).
      let stat: fs.BigIntStats;
      try {
        stat = fs.lstatSync(absPath, { bigint: true }) as fs.BigIntStats;
      } catch (err: unknown) {
        throw new ContentIntegrityError(
          `Cannot stat "${absPath}": ${err instanceof Error ? err.message : String(err)}`,
          'stat_error',
        );
      }

      // lstat would return isSymbolicLink()=true for symlinks; for Windows
      // junctions, Node reports isDirectory()=true but isSymbolicLink()=false.
      // We catch those via the ancestor chain check at the higher level.  The
      // best we can do here for direct children is to check isSymbolicLink().
      if (stat.isSymbolicLink()) {
        throw new ContentIntegrityError(
          `Symbolic link not allowed in installed content: "${relPath}"`,
          'unsafe_content',
        );
      }

      if (stat.isDirectory()) {
        dirs.push({ relPath, absPath });
        await walk(absPath, relPath);
      } else if (stat.isFile()) {
        fileCount++;
        if (fileCount > limits.maxFiles) {
          throw new ContentIntegrityError(
            `File count ${fileCount} exceeds maximum ${limits.maxFiles}`,
            'too_many_files',
          );
        }

        const fileSize = Number(stat.size);
        totalBytes += fileSize;
        if (totalBytes > limits.maxBytes) {
          throw new ContentIntegrityError(
            `Total bytes ${totalBytes} exceeds maximum ${limits.maxBytes}`,
            'too_large',
          );
        }

        files.push({
          relPath,
          size: fileSize,
          absPath,
          identity: { dev: stat.dev, ino: stat.ino, size: stat.size },
        });
      } else if (stat.isSocket()) {
        throw new ContentIntegrityError(
          `Socket not allowed in installed content: "${relPath}"`,
          'unsafe_content',
        );
      } else if (stat.isFIFO()) {
        throw new ContentIntegrityError(
          `FIFO not allowed in installed content: "${relPath}"`,
          'unsafe_content',
        );
      } else if (stat.isBlockDevice() || stat.isCharacterDevice()) {
        throw new ContentIntegrityError(
          `Device file not allowed in installed content: "${relPath}"`,
          'unsafe_content',
        );
      }
      // Unknown types — skip silently (safe: won't contribute to hash)
    }
  }

  await walk(root, '');

  // Sort by relative path with locale-independent binary comparison
  dirs.sort((a, b) => binaryCompare(a.relPath, b.relPath));
  files.sort((a, b) => binaryCompare(a.relPath, b.relPath));

  return { dirs, files };
}

/**
 * Stream the content of `absPath` into `hash`, enforcing the byte limit in
 * real time.
 *
 * TOCTOU defence:
 * 1. `identity` was captured during the initial `lstat` pass.
 * 2. After `fs.openSync`, we `fstat` the fd and compare dev/ino/size against
 *    the saved identity.  If the file was swapped (symlink, junction, rename,
 *    truncation) between lstat and open, this mismatch is detected.
 * 3. We verify the realpath of the opened file is still within `realRoot`.
 *
 * Never loads the full file into memory — maximum allocation is CHUNK_SIZE.
 */
function hashFileContent(
  absPath: string,
  relPath: string,
  identity: FileIdentity,
  realRoot: string,
  hash: crypto.Hash,
  bytesSoFar: number,
  maxBytes: number,
): number {
  // O_NOFOLLOW on POSIX platforms prevents the kernel from following a
  // symlink that may have been swapped in after our lstat.  On Windows this
  // flag is not available; identity comparison and realpath provide the
  // defence there.
  const openFlags: number = process.platform === 'win32'
    ? fs.constants.O_RDONLY
    : fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW;

  let fd: number | undefined;
  try {
    fd = fs.openSync(absPath, openFlags);
  } catch (err: unknown) {
    throw new ContentIntegrityError(
      `Cannot open file "${relPath}": ${err instanceof Error ? err.message : String(err)}`,
      'read_error',
    );
  }

  try {
    // fstat after open (with bigint for full precision) — compare identity
    let fdStat: fs.BigIntStats;
    try {
      fdStat = fs.fstatSync(fd, { bigint: true }) as fs.BigIntStats;
    } catch (err: unknown) {
      throw new ContentIntegrityError(
        `Cannot fstat file "${relPath}": ${err instanceof Error ? err.message : String(err)}`,
        'read_error',
      );
    }

    if (!fdStat.isFile()) {
      throw new ContentIntegrityError(
        `File "${relPath}" is no longer a regular file`,
        'unsafe_content',
      );
    }

    // Identity check: dev+ino must match the initial bigint lstat.  If the
    // file was swapped (symlink replaced with different file, junction
    // redirect, etc.) these will differ.
    if (fdStat.dev !== identity.dev || fdStat.ino !== identity.ino) {
      throw new ContentIntegrityError(
        `File "${relPath}" was replaced between scan and read (identity mismatch)`,
        'unsafe_content',
      );
    }

    // Size check: if size changed, the file was modified between lstat and
    // open (truncation, append, etc.)
    if (fdStat.size !== identity.size) {
      throw new ContentIntegrityError(
        `File "${relPath}" size changed between scan and read (was ${identity.size}, now ${fdStat.size})`,
        'unsafe_content',
      );
    }

    // Physical containment check: ensure the opened file's realpath is within
    // the real root (guards against mount-point swaps and junction redirects
    // that preserve dev/ino).
    let realPath: string;
    try {
      realPath = fs.realpathSync(absPath);
    } catch {
      throw new ContentIntegrityError(
        `Cannot resolve real path of "${relPath}"`,
        'unsafe_content',
      );
    }
    if (!realPath.startsWith(realRoot + path.sep) && realPath !== realRoot) {
      throw new ContentIntegrityError(
        `File "${relPath}" real path "${realPath}" is outside root "${realRoot}"`,
        'unsafe_content',
      );
    }

    // Read in chunks, updating both the hash and the byte counter
    const buf = Buffer.allocUnsafe(CHUNK_SIZE);
    let fileBytesRead = 0;

    while (true) {
      let bytesRead: number;
      try {
        bytesRead = fs.readSync(fd, buf, 0, buf.length, null);
      } catch (err: unknown) {
        throw new ContentIntegrityError(
          `Cannot read file "${relPath}": ${err instanceof Error ? err.message : String(err)}`,
          'read_error',
        );
      }

      if (bytesRead === 0) break; // EOF

      fileBytesRead += bytesRead;
      const currentTotal = bytesSoFar + fileBytesRead;
      if (currentTotal > maxBytes) {
        throw new ContentIntegrityError(
          `Content exceeds maximum of ${maxBytes} bytes while reading "${relPath}"`,
          'too_large',
        );
      }

      hash.update(buf.subarray(0, bytesRead));
    }

    return fileBytesRead;
  } finally {
    try { fs.closeSync(fd); } catch { /* best-effort */ }
  }
}

/**
 * Compute a deterministic content digest of a directory tree.
 *
 * The root must be a plain directory — symlinks and reparse points are
 * rejected up front so the verifier cannot be tricked into hashing a
 * different part of the filesystem.
 */
export async function computeDirectoryDigest(
  root: string,
  limits?: DigestLimits,
): Promise<DirectoryDigest> {
  // Resolve to absolute path for safety checks
  const resolvedRoot = path.resolve(root);

  // Verify root is a plain directory (not a symlink)
  let rootStat: fs.BigIntStats;
  try {
    rootStat = fs.lstatSync(resolvedRoot, { bigint: true }) as fs.BigIntStats;
  } catch (err: unknown) {
    throw new ContentIntegrityError(
      `Cannot access directory "${resolvedRoot}": ${err instanceof Error ? err.message : String(err)}`,
      'missing',
    );
  }

  if (rootStat.isSymbolicLink()) {
    throw new ContentIntegrityError(
      `Root path is a symbolic link — must be a real directory: "${resolvedRoot}"`,
      'unsafe_content',
    );
  }

  if (!rootStat.isDirectory()) {
    throw new ContentIntegrityError(
      `Path is not a directory: "${resolvedRoot}"`,
      'missing',
    );
  }

  const effectiveLimits: Required<DigestLimits> = {
    maxFiles: limits?.maxFiles ?? DEFAULT_MAX_FILES,
    maxBytes: limits?.maxBytes ?? DEFAULT_MAX_BYTES,
  };

  // Collect all entries (validated, sorted) — metadata only, no file content
  const { dirs, files } = await collectEntries(resolvedRoot, effectiveLimits);

  // Resolve the real root for physical containment checks during file reads
  let realRoot: string;
  try {
    realRoot = fs.realpathSync(resolvedRoot);
  } catch {
    throw new ContentIntegrityError(
      `Cannot resolve real path of root "${resolvedRoot}"`,
      'unsafe_content',
    );
  }

  // Build the hash input — stream file content in chunks
  const hash = crypto.createHash('sha256');
  let fileCount = 0;
  let totalBytes = 0;

  // Hash all directory entries first
  for (const e of dirs) {
    hash.update('D\0');
    hash.update(e.relPath);
    hash.update('\0');
  }

  // Hash all file entries — open/fstat/stream each file with TOCTOU defence
  for (const e of files) {
    fileCount++;
    totalBytes += e.size;

    hash.update('F\0');
    hash.update(e.relPath);
    hash.update('\0');
    hash.update(String(e.size));
    hash.update('\0');

    // Stream file content with real-time byte enforcement, identity
    // verification, and physical containment check
    hashFileContent(
      e.absPath, e.relPath, e.identity, realRoot,
      hash, totalBytes - e.size, effectiveLimits.maxBytes,
    );

    hash.update('\0');
  }

  return {
    algorithm: CONTENT_HASH_ALGORITHM,
    digest: hash.digest('hex'),
    fileCount,
    totalBytes,
  };
}
