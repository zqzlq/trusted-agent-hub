/**
 * Tests for deterministic content digest (content-integrity.ts).
 *
 * Run: npx tsx tests/content-integrity.test.ts
 */

import * as assert from 'assert';
import * as crypto from 'crypto';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import * as net from 'net';
import { execFileSync } from 'child_process';

import {
  CONTENT_HASH_ALGORITHM,
  computeDirectoryDigest,
  ContentIntegrityError,
} from '../src/content-integrity';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeTmpDir(): string {
  const dir = path.join(os.tmpdir(), 'tah-digest-test-' + crypto.randomBytes(4).toString('hex'));
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function writeFile(dir: string, name: string, content: string | Buffer): void {
  const filePath = path.join(dir, name);
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content);
}

function cleanup(dir: string): void {
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* ignore */ }
}

let passed = 0;
let failed = 0;

function runTest(name: string, fn: () => Promise<void>) {
  return fn().then(
    () => { passed++; console.log(`  ✓ ${name}`); },
    (err: unknown) => {
      failed++;
      console.log(`  ✗ ${name}`);
      console.error(err instanceof Error ? err.stack || err.message : String(err));
    },
  );
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  console.log('CLI Content Integrity Tests\n');

  // -----------------------------------------------------------------------
  // Empty directory
  // -----------------------------------------------------------------------

  await runTest('Empty directory produces valid digest', async () => {
    const dir = makeTmpDir();
    try {
      const digest = await computeDirectoryDigest(dir);
      assert.strictEqual(digest.algorithm, CONTENT_HASH_ALGORITHM);
      assert.strictEqual(digest.fileCount, 0);
      assert.strictEqual(digest.totalBytes, 0);
      assert.strictEqual(digest.digest.length, 64);
      assert.ok(/^[a-f0-9]{64}$/.test(digest.digest));
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // Stable across repeated computations
  // -----------------------------------------------------------------------

  await runTest('Repeated computation produces identical digest', async () => {
    const dir = makeTmpDir();
    try {
      writeFile(dir, 'a.txt', 'hello');
      writeFile(dir, 'sub/b.txt', 'world');

      const d1 = await computeDirectoryDigest(dir);
      const d2 = await computeDirectoryDigest(dir);
      assert.strictEqual(d1.digest, d2.digest);
      assert.strictEqual(d1.fileCount, d2.fileCount);
      assert.strictEqual(d1.totalBytes, d2.totalBytes);
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // Order-independent
  // -----------------------------------------------------------------------

  await runTest('Creation order does not affect digest', async () => {
    const dir1 = makeTmpDir();
    const dir2 = makeTmpDir();
    try {
      writeFile(dir1, 'c.txt', 'ccc');
      writeFile(dir1, 'a.txt', 'aaa');
      writeFile(dir1, 'b.txt', 'bbb');

      writeFile(dir2, 'b.txt', 'bbb');
      writeFile(dir2, 'c.txt', 'ccc');
      writeFile(dir2, 'a.txt', 'aaa');

      const d1 = await computeDirectoryDigest(dir1);
      const d2 = await computeDirectoryDigest(dir2);
      assert.strictEqual(d1.digest, d2.digest);
    } finally {
      cleanup(dir1);
      cleanup(dir2);
    }
  });

  // -----------------------------------------------------------------------
  // Content change
  // -----------------------------------------------------------------------

  await runTest('Content change detected', async () => {
    const dir = makeTmpDir();
    try {
      writeFile(dir, 'a.txt', 'hello');
      const d1 = await computeDirectoryDigest(dir);

      writeFile(dir, 'a.txt', 'world');
      const d2 = await computeDirectoryDigest(dir);

      assert.notStrictEqual(d1.digest, d2.digest);
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // File addition
  // -----------------------------------------------------------------------

  await runTest('File addition detected', async () => {
    const dir = makeTmpDir();
    try {
      writeFile(dir, 'a.txt', 'hello');
      const d1 = await computeDirectoryDigest(dir);

      writeFile(dir, 'b.txt', 'world');
      const d2 = await computeDirectoryDigest(dir);

      assert.notStrictEqual(d1.digest, d2.digest);
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // File deletion
  // -----------------------------------------------------------------------

  await runTest('File deletion detected', async () => {
    const dir = makeTmpDir();
    try {
      writeFile(dir, 'a.txt', 'hello');
      writeFile(dir, 'b.txt', 'world');
      const d1 = await computeDirectoryDigest(dir);

      fs.unlinkSync(path.join(dir, 'b.txt'));
      const d2 = await computeDirectoryDigest(dir);

      assert.notStrictEqual(d1.digest, d2.digest);
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // File rename
  // -----------------------------------------------------------------------

  await runTest('File rename detected', async () => {
    const dir = makeTmpDir();
    try {
      writeFile(dir, 'a.txt', 'hello');
      const d1 = await computeDirectoryDigest(dir);

      fs.renameSync(path.join(dir, 'a.txt'), path.join(dir, 'b.txt'));
      const d2 = await computeDirectoryDigest(dir);

      assert.notStrictEqual(d1.digest, d2.digest);
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // Nested directory change
  // -----------------------------------------------------------------------

  await runTest('Nested directory change detected', async () => {
    const dir = makeTmpDir();
    try {
      writeFile(dir, 'sub/a.txt', 'hello');
      const d1 = await computeDirectoryDigest(dir);

      writeFile(dir, 'sub/a.txt', 'changed');
      const d2 = await computeDirectoryDigest(dir);

      assert.notStrictEqual(d1.digest, d2.digest);
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // Symlink rejected
  // -----------------------------------------------------------------------

  await runTest('Symlink rejected', async () => {
    const dir = makeTmpDir();
    try {
      writeFile(dir, 'real.txt', 'content');

      // Try to create a symlink (may fail on Windows without privileges)
      try {
        fs.symlinkSync(path.join(dir, 'real.txt'), path.join(dir, 'link.txt'));
      } catch {
        // Cannot create symlink — skip validation, test passes
        return;
      }

      try {
        await computeDirectoryDigest(dir);
        assert.fail('Should have thrown');
      } catch (e: unknown) {
        assert.ok(e instanceof ContentIntegrityError);
        assert.strictEqual((e as ContentIntegrityError).code, 'unsafe_content');
      }
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // Root symlink rejected
  // -----------------------------------------------------------------------

  await runTest('Root symlink rejected', async () => {
    const dir = makeTmpDir();
    try {
      const realDir = path.join(dir, 'real');
      fs.mkdirSync(realDir);
      writeFile(realDir, 'a.txt', 'hello');

      try {
        fs.symlinkSync(realDir, path.join(dir, 'link'), 'dir');
      } catch {
        // Cannot create symlink — skip
        return;
      }

      try {
        await computeDirectoryDigest(path.join(dir, 'link'));
        assert.fail('Should have thrown');
      } catch (e: unknown) {
        assert.ok(e instanceof ContentIntegrityError);
        assert.strictEqual((e as ContentIntegrityError).code, 'unsafe_content');
      }
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // POSIX special files
  // -----------------------------------------------------------------------

  await runTest('FIFO rejected on POSIX', async () => {
    if (process.platform === 'win32') return;
    const dir = makeTmpDir();
    try {
      execFileSync('mkfifo', [path.join(dir, 'unsafe.fifo')]);
      await assert.rejects(
        () => computeDirectoryDigest(dir),
        (error: unknown) => error instanceof ContentIntegrityError && error.code === 'unsafe_content',
      );
    } finally {
      cleanup(dir);
    }
  });

  await runTest('Unix socket rejected on POSIX', async () => {
    if (process.platform === 'win32') return;
    const dir = makeTmpDir();
    const socketPath = path.join(dir, 'unsafe.sock');
    const server = net.createServer();
    try {
      await new Promise<void>((resolve, reject) => {
        server.once('error', reject);
        server.listen(socketPath, resolve);
      });
      await assert.rejects(
        () => computeDirectoryDigest(dir),
        (error: unknown) => error instanceof ContentIntegrityError && error.code === 'unsafe_content',
      );
    } finally {
      await new Promise<void>((resolve) => server.close(() => resolve()));
      cleanup(dir);
    }
  });

  await runTest('Character device rejected in Linux CI', async () => {
    if (process.platform !== 'linux' || !process.env.CI) return;
    const dir = makeTmpDir();
    try {
      const devicePath = path.join(dir, 'unsafe-device');
      if (typeof process.getuid === 'function' && process.getuid() === 0) {
        execFileSync('mknod', [devicePath, 'c', '1', '3']);
      } else {
        execFileSync('sudo', ['-n', 'mknod', devicePath, 'c', '1', '3']);
      }
      await assert.rejects(
        () => computeDirectoryDigest(dir),
        (error: unknown) => error instanceof ContentIntegrityError && error.code === 'unsafe_content',
      );
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // Non-existent path
  // -----------------------------------------------------------------------

  await runTest('Non-existent path rejected', async () => {
    try {
      await computeDirectoryDigest(path.join(os.tmpdir(), 'does-not-exist-' + crypto.randomBytes(8).toString('hex')));
      assert.fail('Should have thrown');
    } catch (e: unknown) {
      assert.ok(e instanceof ContentIntegrityError);
      assert.strictEqual((e as ContentIntegrityError).code, 'missing');
    }
  });

  // -----------------------------------------------------------------------
  // File instead of directory
  // -----------------------------------------------------------------------

  await runTest('File-instead-of-directory rejected', async () => {
    const dir = makeTmpDir();
    try {
      const filePath = path.join(dir, 'file.txt');
      fs.writeFileSync(filePath, 'hello');
      try {
        await computeDirectoryDigest(filePath);
        assert.fail('Should have thrown');
      } catch (e: unknown) {
        assert.ok(e instanceof ContentIntegrityError);
        assert.strictEqual((e as ContentIntegrityError).code, 'missing');
      }
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // Binary file content
  // -----------------------------------------------------------------------

  await runTest('Binary files digest correctly', async () => {
    const dir1 = makeTmpDir();
    const dir2 = makeTmpDir();
    try {
      const binaryContent = crypto.randomBytes(1024);
      writeFile(dir1, 'binary.bin', binaryContent);
      writeFile(dir2, 'binary.bin', binaryContent);

      const d1 = await computeDirectoryDigest(dir1);
      const d2 = await computeDirectoryDigest(dir2);
      assert.strictEqual(d1.digest, d2.digest);
      assert.strictEqual(d1.fileCount, 1);
      assert.strictEqual(d1.totalBytes, 1024);
    } finally {
      cleanup(dir1);
      cleanup(dir2);
    }
  });

  // -----------------------------------------------------------------------
  // Many files
  // -----------------------------------------------------------------------

  await runTest('Many files (100) computed correctly', async () => {
    const dir = makeTmpDir();
    try {
      for (let i = 0; i < 100; i++) {
        writeFile(dir, `file_${String(i).padStart(3, '0')}.txt`, `content ${i}`);
      }

      const d1 = await computeDirectoryDigest(dir);
      assert.strictEqual(d1.fileCount, 100);

      const d2 = await computeDirectoryDigest(dir);
      assert.strictEqual(d1.digest, d2.digest);

      // Modify one file
      writeFile(dir, 'file_050.txt', 'changed');
      const d3 = await computeDirectoryDigest(dir);
      assert.notStrictEqual(d1.digest, d3.digest);
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // File count limit
  // -----------------------------------------------------------------------

  await runTest('File count limit exceeded', async () => {
    const dir = makeTmpDir();
    try {
      for (let i = 0; i < 15; i++) {
        writeFile(dir, `f${i}.txt`, 'x');
      }

      try {
        await computeDirectoryDigest(dir, { maxFiles: 10 });
        assert.fail('Should have thrown');
      } catch (e: unknown) {
        assert.ok(e instanceof ContentIntegrityError);
        assert.strictEqual((e as ContentIntegrityError).code, 'too_many_files');
      }
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // Byte size limit
  // -----------------------------------------------------------------------

  await runTest('Byte size limit exceeded', async () => {
    const dir = makeTmpDir();
    try {
      writeFile(dir, 'big.txt', Buffer.alloc(5000, 'x'));
      try {
        await computeDirectoryDigest(dir, { maxBytes: 1000 });
        assert.fail('Should have thrown');
      } catch (e: unknown) {
        assert.ok(e instanceof ContentIntegrityError);
        assert.strictEqual((e as ContentIntegrityError).code, 'too_large');
      }
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // Deep nesting
  // -----------------------------------------------------------------------

  await runTest('Deep nesting works', async () => {
    const dir = makeTmpDir();
    try {
      writeFile(dir, 'a/b/c/d/e/f/g/h.txt', 'deep');
      const d = await computeDirectoryDigest(dir);
      assert.strictEqual(d.fileCount, 1);
      assert.strictEqual(d.digest.length, 64);
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // Digest format
  // -----------------------------------------------------------------------

  await runTest('Digest format is correct', async () => {
    const dir = makeTmpDir();
    try {
      writeFile(dir, 'test.txt', 'hello world');
      const d = await computeDirectoryDigest(dir);
      assert.strictEqual(d.algorithm, 'sha256-tree-v1');
      assert.strictEqual(d.digest.length, 64);
      assert.ok(/^[a-f0-9]{64}$/.test(d.digest));
      assert.strictEqual(d.fileCount, 1);
      assert.strictEqual(d.totalBytes, 11);
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // Empty subdirectories contribute to hash
  // -----------------------------------------------------------------------

  await runTest('Empty subdirectory changes digest', async () => {
    const dir1 = makeTmpDir();
    const dir2 = makeTmpDir();
    try {
      writeFile(dir1, 'a.txt', 'hello');
      writeFile(dir2, 'a.txt', 'hello');
      fs.mkdirSync(path.join(dir2, 'empty_sub'));

      const d1 = await computeDirectoryDigest(dir1);
      const d2 = await computeDirectoryDigest(dir2);

      assert.notStrictEqual(d1.digest, d2.digest);
    } finally {
      cleanup(dir1);
      cleanup(dir2);
    }
  });

  // -----------------------------------------------------------------------
  // Fixed test vector — ensures algorithm doesn't drift
  // -----------------------------------------------------------------------

  await runTest('Fixed test vector for sha256-tree-v1', async () => {
    // This known file tree MUST produce the same digest on all platforms
    // (Windows and Linux).  If this test fails the algorithm has drifted.
    const EXPECTED_DIGEST = '6c25f5c00a57e88da50bd24cca649d0a8e76bb404e78ffb5a53e2ac8e90d5bcc';

    const dir = makeTmpDir();
    try {
      writeFile(dir, 'README.md', 'Hello World');
      writeFile(dir, 'src/main.ts', 'export const x = 1;');

      const digest = await computeDirectoryDigest(dir);
      assert.strictEqual(digest.algorithm, 'sha256-tree-v1');
      assert.strictEqual(digest.fileCount, 2);
      assert.strictEqual(digest.digest, EXPECTED_DIGEST);

      // Recreate the same tree in a different directory — must produce same digest
      const dir2 = makeTmpDir();
      try {
        writeFile(dir2, 'README.md', 'Hello World');
        writeFile(dir2, 'src/main.ts', 'export const x = 1;');
        const digest2 = await computeDirectoryDigest(dir2);
        assert.strictEqual(digest2.digest, EXPECTED_DIGEST);
        assert.strictEqual(digest2.fileCount, 2);
      } finally {
        cleanup(dir2);
      }
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // validateAncestorChain — normal directory
  // -----------------------------------------------------------------------

  await runTest('validateAncestorChain accepts normal directories', async () => {
    const { validateAncestorChain } = require('../src/content-integrity');
    const dir = makeTmpDir();
    try {
      writeFile(dir, 'a.txt', 'hello');
      // Should not throw
      validateAncestorChain(dir);
    } finally {
      cleanup(dir);
    }
  });

  // -----------------------------------------------------------------------
  // validateAncestorChain — non-existent path
  // -----------------------------------------------------------------------

  await runTest('validateAncestorChain rejects non-existent path', async () => {
    const { validateAncestorChain } = require('../src/content-integrity');
    try {
      validateAncestorChain(path.join(os.tmpdir(), 'does-not-exist-xyz-12345'));
      assert.fail('Should have thrown');
    } catch (e: unknown) {
      assert.ok(e instanceof ContentIntegrityError);
      assert.strictEqual((e as ContentIntegrityError).code, 'unsafe_content');
    }
  });

  // -----------------------------------------------------------------------

  console.log(`\n  ✓ ${passed} passed` + (failed ? `  ✗ ${failed} failed` : '') + '\n');
  if (failed) process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
