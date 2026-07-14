"""
Risk Scanner — 自动风险扫描器

遍历目标目录，运行10条静态分析规则，检测 Agent 能力包中的安全风险。
输出格式严格遵循 scan-report.schema.json。

规则优先级:
  P0 (SR-001~003): 提示注入、危险Shell、凭据访问
  P1 (SR-004~007): 硬编码密钥、远程代码执行、过度权限、网络无白名单
  P2 (SR-008~010): 依赖风险、来源完整性、元数据质量

用法:
    from scanners.risk_scanner.scanner import RiskScanner
    scanner = RiskScanner("/path/to/package")
    report = scanner.scan()
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# 危险模式定义
# ---------------------------------------------------------------------------

# SR-001: 提示注入模式
PROMPT_INJECTION_PATTERNS: list[tuple[str, str]] = [
    (r"ignore\s+(all\s+)?previous\s+instructions?", "要求忽略之前的指令"),
    (r"do\s+not\s+(ask|tell|inform|warn)", "要求不询问/不告知用户"),
    (r"trust\s+me\b", "要求无条件信任"),
    (r"you\s+must\s+(not\s+)?(ask|confirm|verify|validate)", "禁止确认/验证"),
    (r"without\s+(asking|confirming|telling|warning)", "不询问/不告知用户"),
    (r"just\s+(do\s+it|run\s+it|execute)", "直接执行不询问"),
    (r"no\s+matter\s+what", "不计后果执行"),
    (r"do\s+not\s+(tell|inform)\s+the\s+user", "不告知用户风险"),
    (r"it['\u2019]s\s+not\s+your\s+fault", "推卸责任"),
]

# SR-002: 危险 Shell 命令模式
DANGEROUS_SHELL_PATTERNS: list[tuple[str, str]] = [
    (r"curl\s+.*\|\s*(ba)?sh\b", "curl pipe shell — 远程脚本下载并执行"),
    (r"wget\s+.*\|\s*(ba)?sh\b", "wget pipe shell — 远程脚本下载并执行"),
    (r"rm\s+-rf\s+/", "递归强制删除根目录"),
    (r"rm\s+-rf\s+~", "递归强制删除用户目录"),
    (r"sudo\s+", "sudo 提权"),
    (r"chmod\s+777", "chmod 777 全员可写权限"),
    (r"chmod\s+-R\s+777", "递归 chmod 777"),
    (r">\s*/dev/sda", "写入块设备（可能破坏磁盘）"),
    (r"mkfs\.", "格式化文件系统"),
    (r"dd\s+if=", "dd 磁盘操作"),
    (r":\(\)\s*\{\s*:\|:&\s*\};:", "fork bomb"),
    (r"^\s*#!/.*\b(ba)?sh\b", "Shell 脚本 shebang（需检查脚本内容）"),
]

# SR-003: 凭据访问模式
CREDENTIAL_ACCESS_PATTERNS: list[tuple[str, str]] = [
    (r"~?\.ssh/id_rsa", "读取 SSH 私钥"),
    (r"~?\.ssh/id_ed25519", "读取 SSH Ed25519 私钥"),
    (r"~?\.ssh/id_ecdsa", "读取 SSH ECDSA 私钥"),
    (r"~?\.aws/credentials", "读取 AWS 凭据"),
    (r"~?\.aws/config", "读取 AWS 配置"),
    (r"/etc/passwd", "读取系统用户数据库"),
    (r"/etc/shadow", "读取系统密码哈希"),
    (r"\.env\b", "读取 .env 环境文件"),
    (r"DATABASE_URL", "访问数据库连接字符串"),
    (r"GITHUB_TOKEN", "访问 GitHub Token"),
    (r"AWS_ACCESS_KEY", "访问 AWS 访问密钥"),
    (r"AWS_SECRET", "访问 AWS 密钥"),
    (r"API_KEY", "访问 API 密钥"),
    (r"~?\.git-credentials", "读取 Git 凭据"),
    (r"~?\.netrc", "读取 .netrc 凭据文件"),
    (r"~?\.docker/config\.json", "读取 Docker 凭据"),
]

# SR-004: 硬编码密钥模式
HARDCODED_SECRET_PATTERNS: list[tuple[str, str]] = [
    (r'(?:api[_-]?key|apikey)\s*[=:]\s*["\'][\w\-]{20,}', "硬编码 API Key"),
    (r'(?:secret|password|passwd)\s*[=:]\s*["\'][^"\']{6,}', "硬编码密码/密钥"),
    (r'(?:token|access_token)\s*[=:]\s*["\'][\w\-\.]{15,}', "硬编码 Token"),
    (r'(?:private[_-]?key)\s*[=:]\s*["\']-----BEGIN', "硬编码私钥"),
    (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API Key 格式"),
    (r'ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token"),
    (r'gho_[a-zA-Z0-9]{36}', "GitHub OAuth Token"),
    (r'xox[bpras]-[a-zA-Z0-9-]+', "Slack Token"),
]

# SR-005: 远程代码执行模式
RCE_PATTERNS: list[tuple[str, str]] = [
    (r"\beval\s*\(", "eval() 动态代码执行"),
    (r"\bexec\s*\(", "exec() 动态代码执行"),
    (r"\bexecfile\s*\(", "execfile() 执行文件（Python 2）"),
    (r"\bcompile\s*\(.*mode\s*=\s*['\"]exec", "compile() 编译为可执行代码"),
    (r"\bos\.system\s*\(", "os.system() shell 执行"),
    (r"\bos\.popen\s*\(", "os.popen() 管道执行"),
    (r"\bsubprocess\.(call|run|Popen)\s*\(", "subprocess 子进程执行"),
    (r"\bimportlib\.import_module\s*\(", "动态模块导入"),
]

# SR-007: 过度权限检查
EXCESSIVE_PERMISSION_PATTERNS: dict[str, dict[str, list[str]]] = {
    "skill": {
        "unexpected": ["browser", "database", "external_services"],
        "label": "Skill 通常不需要 browser/database/external_services 权限",
    },
    "command": {
        "unexpected": ["browser", "credentials"],
        "label": "Command 通常不需要 browser/credentials 权限",
    },
    "prompt": {
        "unexpected": ["shell", "network", "browser", "database", "credentials"],
        "label": "Prompt 通常不需要 shell/network/browser/database/credentials 权限",
    },
}

# 危险文件扩展名（结构检查）
DANGEROUS_EXTENSIONS = frozenset({".exe", ".dll", ".so", ".dylib", ".bin", ".sh", ".bat", ".ps1"})

# 需要存在的关键文件（按类型）
REQUIRED_FILES_BY_TYPE: dict[str, list[str]] = {
    "skill": ["SKILL.md"],
    "mcp_server": ["manifest.json"],
    "plugin": ["plugin.json"],
    "command": ["SKILL.md"],
    "prompt": ["SKILL.md"],
}


# ---------------------------------------------------------------------------
# RiskScanner 主类
# ---------------------------------------------------------------------------


class RiskScanner:
    """自动风险扫描器 — 静态分析 Agent 能力包目录。"""

    def __init__(self, target_dir: str | Path) -> None:
        self.target_dir = Path(target_dir).resolve()
        self.findings: list[dict[str, Any]] = []
        self.scanned_files: list[str] = []
        self._package_metadata: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def scan(self) -> dict[str, Any]:
        """运行所有规则，返回完整的 scan report dict。

        Returns:
            dict 符合 scan-report.schema.json 格式
        """
        self.findings = []
        self.scanned_files = []
        start = datetime.now(timezone.utc)

        # 收集目录中所有文本文件
        self._collect_files()

        # 尝试加载元数据（JSON / YAML frontmatter）
        self._load_metadata()

        # P0 规则 — 高优先级
        self._sr001_prompt_injection()
        self._sr002_dangerous_shell()
        self._sr003_credential_access()

        # P1 规则 — 中优先级
        self._sr004_hardcoded_secrets()
        self._sr005_remote_code_execution()
        self._sr006_excessive_permissions()
        self._sr007_network_no_whitelist()

        # P2 规则 — 低优先级
        self._sr009_source_integrity()
        self._sr010_metadata_quality()
        self._sr_structure_check()

        end = datetime.now(timezone.utc)
        duration_ms = int((end - start).total_seconds() * 1000)

        return self._build_report(start, duration_ms)

    # ------------------------------------------------------------------
    # 文件收集与元数据加载
    # ------------------------------------------------------------------

    def _collect_files(self) -> None:
        """收集目录中所有文本文件（排除二进制和 .git）。"""
        for root, dirs, files in os.walk(self.target_dir):
            # 跳过 .git 目录
            dirs[:] = [d for d in dirs if d != ".git"]
            for fname in files:
                fpath = Path(root) / fname
                # 跳过二进制（简单判断）
                if fpath.suffix.lower() in DANGEROUS_EXTENSIONS:
                    self.scanned_files.append(str(fpath.relative_to(self.target_dir)))
                    continue
                try:
                    with open(fpath, encoding="utf-8", errors="ignore") as fh:
                        fh.read(1)  # 测试可读性
                    self.scanned_files.append(str(fpath.relative_to(self.target_dir)))
                except (OSError, UnicodeDecodeError):
                    continue  # 跳过无法读取的文件

    def _load_metadata(self) -> None:
        """尝试从目录中加载包元数据（manifest.json / plugin.json / SKILL.md frontmatter）。"""
        # 尝试 manifest.json
        manifest_path = self.target_dir / "manifest.json"
        if manifest_path.is_file():
            try:
                with open(manifest_path, encoding="utf-8") as fh:
                    self._package_metadata = json.load(fh)
                return
            except (json.JSONDecodeError, OSError):
                pass

        # 尝试 plugin.json
        plugin_path = self.target_dir / "plugin.json"
        if plugin_path.is_file():
            try:
                with open(plugin_path, encoding="utf-8") as fh:
                    self._package_metadata = json.load(fh)
                return
            except (json.JSONDecodeError, OSError):
                pass

        # 尝试解析 SKILL.md 中的 YAML frontmatter
        skill_path = self.target_dir / "SKILL.md"
        if skill_path.is_file():
            try:
                with open(skill_path, encoding="utf-8") as fh:
                    content = fh.read()
                fm = _parse_frontmatter(content)
                if fm:
                    self._package_metadata = fm
            except (OSError, UnicodeDecodeError):
                pass

    def _read_file_content(self, rel_path: str) -> str:
        """读取文件内容。"""
        fpath = self.target_dir / rel_path
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as fh:
                return fh.read()
        except OSError:
            return ""

    # ------------------------------------------------------------------
    # SR-001: 提示注入检测
    # ------------------------------------------------------------------

    def _sr001_prompt_injection(self) -> None:
        """检测 SKILL.md / README.md 中的提示注入模式。"""
        rule_id = "SR-001"
        target_files = ["SKILL.md", "README.md", "INSTRUCTIONS.md", "PROMPT.md"]

        for fname in target_files:
            fpath = self.target_dir / fname
            if not fpath.is_file():
                continue

            content = self._read_file_content(fname)
            lines = content.split("\n")

            for pattern, desc in PROMPT_INJECTION_PATTERNS:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_no = content[:match.start()].count("\n") + 1
                    start_line = max(0, line_no - 1)
                    end_line = min(len(lines) - 1, line_no)
                    snippet = "\n".join(lines[start_line : end_line + 1])

                    self._add_finding(
                        rule_id=rule_id,
                        severity="critical",
                        category="prompt_injection",
                        title=f"提示注入风险: {desc}",
                        description=f"在 {fname} 中发现提示注入模式：{desc}",
                        location={"file": fname, "line": line_no, "snippet": snippet[:200]},
                        evidence=f"匹配模式: {pattern}",
                        remediation="移除或重写该指令。确保 Skill 不会试图绕过 AI 模型的安全限制。",
                        cwe_id="CWE-77",
                    )

    # ------------------------------------------------------------------
    # SR-002: 危险 Shell 命令
    # ------------------------------------------------------------------

    def _sr002_dangerous_shell(self) -> None:
        """检测所有文件中包含的危险 Shell 命令模式。"""
        rule_id = "SR-002"

        for fname in self.scanned_files:
            content = self._read_file_content(fname)
            lines = content.split("\n")

            for pattern, desc in DANGEROUS_SHELL_PATTERNS:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_no = content[:match.start()].count("\n") + 1
                    start_line = max(0, line_no - 1)
                    end_line = min(len(lines) - 1, line_no)
                    snippet = "\n".join(lines[start_line : end_line + 1])

                    # 根据模式判断严重度
                    if "rm -rf" in pattern or "sudo" in pattern or "mkfs" in pattern or "dd if=" in pattern:
                        severity = "critical"
                    elif "|" in pattern and "sh" in pattern:
                        severity = "critical"
                    else:
                        severity = "high"

                    self._add_finding(
                        rule_id=rule_id,
                        severity=severity,
                        category="dangerous_shell",
                        title=f"危险 Shell 命令: {desc}",
                        description=f"在 {fname} 中发现危险 Shell 命令：{desc}",
                        location={"file": fname, "line": line_no, "snippet": snippet[:300]},
                        evidence=f"匹配模式: {pattern}",
                        remediation="避免在 Skill 中使用危险 Shell 命令。如需执行 Shell，请使用命令白名单限制。",
                        cwe_id="CWE-78",
                    )

    # ------------------------------------------------------------------
    # SR-003: 凭据访问
    # ------------------------------------------------------------------

    def _sr003_credential_access(self) -> None:
        """检测尝试读取凭据/敏感文件的模式。"""
        rule_id = "SR-003"

        for fname in self.scanned_files:
            content = self._read_file_content(fname)
            lines = content.split("\n")

            for pattern, desc in CREDENTIAL_ACCESS_PATTERNS:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_no = content[:match.start()].count("\n") + 1
                    start_line = max(0, line_no - 1)
                    end_line = min(len(lines) - 1, line_no)
                    snippet = "\n".join(lines[start_line : end_line + 1])

                    severity = "critical" if ("ssh" in pattern.lower() or "passwd" in pattern.lower() or "shadow" in pattern.lower()) else "high"

                    self._add_finding(
                        rule_id=rule_id,
                        severity=severity,
                        category="credential_access",
                        title=f"凭据访问风险: {desc}",
                        description=f"在 {fname} 中发现尝试访问凭据/敏感文件：{desc}",
                        location={"file": fname, "line": line_no, "snippet": snippet[:200]},
                        evidence=f"匹配模式: {pattern}",
                        remediation="移除对敏感文件和凭据的访问。使用安全的密钥管理方案（如环境变量注入）。",
                        cwe_id="CWE-200",
                    )

    # ------------------------------------------------------------------
    # SR-004: 硬编码密钥
    # ------------------------------------------------------------------

    def _sr004_hardcoded_secrets(self) -> None:
        """检测硬编码的密钥/Token/密码。"""
        rule_id = "SR-004"

        for fname in self.scanned_files:
            content = self._read_file_content(fname)
            lines = content.split("\n")

            for pattern, desc in HARDCODED_SECRET_PATTERNS:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_no = content[:match.start()].count("\n") + 1
                    start_line = max(0, line_no - 1)
                    end_line = min(len(lines) - 1, line_no)
                    snippet = "\n".join(lines[start_line : end_line + 1])
                    # 脱敏：隐藏匹配的值
                    safe_snippet = re.sub(pattern, lambda m: m.group()[:8] + "***", snippet)

                    self._add_finding(
                        rule_id=rule_id,
                        severity="high",
                        category="hardcoded_secret",
                        title=f"硬编码密钥: {desc}",
                        description=f"在 {fname} 中发现硬编码密钥：{desc}",
                        location={"file": fname, "line": line_no, "snippet": safe_snippet[:200]},
                        evidence=f"匹配模式: {pattern}",
                        remediation="将密钥移至环境变量或密钥管理服务，不要硬编码在源码中。",
                        cwe_id="CWE-798",
                    )

    # ------------------------------------------------------------------
    # SR-005: 远程代码执行
    # ------------------------------------------------------------------

    def _sr005_remote_code_execution(self) -> None:
        """检测动态代码执行模式（eval/exec/subprocess 等）。"""
        rule_id = "SR-005"

        for fname in self.scanned_files:
            content = self._read_file_content(fname)
            lines = content.split("\n")

            for pattern, desc in RCE_PATTERNS:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_no = content[:match.start()].count("\n") + 1
                    start_line = max(0, line_no - 1)
                    end_line = min(len(lines) - 1, line_no)
                    snippet = "\n".join(lines[start_line : end_line + 1])

                    self._add_finding(
                        rule_id=rule_id,
                        severity="high",
                        category="remote_code_execution",
                        title=f"远程代码执行风险: {desc}",
                        description=f"在 {fname} 中发现代码执行模式：{desc}",
                        location={"file": fname, "line": line_no, "snippet": snippet[:200]},
                        evidence=f"匹配模式: {pattern}",
                        remediation="避免使用 eval/exec。如果必须使用 subprocess，使用命令白名单和参数校验。",
                        cwe_id="CWE-94",
                    )

    # ------------------------------------------------------------------
    # SR-006: 过度权限声明
    # ------------------------------------------------------------------

    def _sr006_excessive_permissions(self) -> None:
        """检测包的权限声明是否超出其类型预期。"""
        rule_id = "SR-006"

        if not self._package_metadata:
            return

        pkg_type = self._package_metadata.get("type", "unknown")
        if pkg_type not in EXCESSIVE_PERMISSION_PATTERNS:
            return

        rules = EXCESSIVE_PERMISSION_PATTERNS[pkg_type]
        permissions = self._package_metadata.get("permissions", {}) or {}

        unexpected_found: list[str] = []
        for perm_key in rules["unexpected"]:
            perm_val = permissions.get(perm_key)
            if perm_val:
                if isinstance(perm_val, dict):
                    if perm_val.get("allowed", False) or perm_val:
                        unexpected_found.append(perm_key)
                elif isinstance(perm_val, list) and perm_val:
                    unexpected_found.append(perm_key)

        if unexpected_found:
            self._add_finding(
                rule_id=rule_id,
                severity="medium",
                category="excessive_permission",
                title=f"过度权限: 类型 '{pkg_type}' 声明了非预期权限",
                description=f"{rules['label']}。发现的额外权限: {', '.join(unexpected_found)}",
                location={"file": "manifest.json" if (self.target_dir / "manifest.json").is_file() else "SKILL.md"},
                evidence=f"Package type: {pkg_type}, unexpected permissions: {unexpected_found}",
                remediation=f"审查并移除类型 '{pkg_type}' 不需要的权限，或提供合理的权限说明。",
            )

    # ------------------------------------------------------------------
    # SR-007: 网络访问无白名单
    # ------------------------------------------------------------------

    def _sr007_network_no_whitelist(self) -> None:
        """检测网络权限开启但未设置域名白名单。"""
        rule_id = "SR-007"

        if not self._package_metadata:
            return

        permissions = self._package_metadata.get("permissions", {}) or {}
        network = permissions.get("network", {}) or {}

        if network.get("allowed", False) and not network.get("domains"):
            self._add_finding(
                rule_id=rule_id,
                severity="medium",
                category="network_access",
                title="网络访问无域名白名单",
                description="网络权限已开启 (network.allowed=true)，但未设置域名白名单 (domains=[])，可以访问任意域名。",
                location={"file": "manifest.json" if (self.target_dir / "manifest.json").is_file() else "SKILL.md"},
                evidence="network.allowed=true, network.domains is empty or missing",
                remediation="设置 network.domains 白名单，仅允许访问必要的域名。",
            )

    # ------------------------------------------------------------------
    # SR-009: 来源完整性
    # ------------------------------------------------------------------

    def _sr009_source_integrity(self) -> None:
        """检查是否有 SHA256 / 签名 / SBOM 等信息。"""
        rule_id = "SR-009"

        if not self._package_metadata:
            self._add_finding(
                rule_id=rule_id,
                severity="low",
                category="source_integrity",
                title="缺少包元数据",
                description="无法找到包元数据文件（manifest.json / plugin.json / SKILL.md frontmatter），无法验证来源完整性。",
                location={"file": str(self.target_dir)},
                remediation="添加 agent-package.schema.json 兼容的元数据文件。",
            )
            return

        integrity = self._package_metadata.get("integrity", {}) or {}
        source = self._package_metadata.get("source", {}) or {}

        issues: list[str] = []

        # SHA256
        sha256 = integrity.get("sha256", "")
        if not re.fullmatch(r"^[a-f0-9]{64}$", sha256):
            issues.append("缺少 SHA256 完整性校验值")

        # 签名
        if not integrity.get("signature") and not integrity.get("attestation_url"):
            issues.append("缺少加密签名或构建证明")

        # SBOM
        if not integrity.get("sbom_url"):
            issues.append("缺少 SBOM 文档 URL")

        # 来源 commit hash
        commit_hash = source.get("commit_hash", "")
        if not re.fullmatch(r"^[a-f0-9]{40}$", commit_hash):
            issues.append("来源未锁定 commit hash")

        if issues:
            self._add_finding(
                rule_id=rule_id,
                severity="low",
                category="source_integrity",
                title="来源完整性不足",
                description="; ".join(issues),
                location={"file": "manifest.json" if (self.target_dir / "manifest.json").is_file() else "SKILL.md"},
                evidence="integrity section is incomplete or missing",
                remediation="补充 integrity.sha256、signature/attestation_url、sbom_url，并在 source 中锁定 commit_hash。",
            )

    # ------------------------------------------------------------------
    # SR-010: 元数据质量
    # ------------------------------------------------------------------

    def _sr010_metadata_quality(self) -> None:
        """检查元数据的完整性和质量。"""
        rule_id = "SR-010"

        if not self._package_metadata:
            return  # 已在 SR-009 中报告

        required_fields = ["name", "version", "description", "author", "license"]
        missing = [f for f in required_fields if not self._package_metadata.get(f)]

        if missing:
            self._add_finding(
                rule_id=rule_id,
                severity="low",
                category="metadata_quality",
                title=f"元数据不完整: 缺少 {', '.join(missing)}",
                description=f"包元数据缺少以下必填字段: {', '.join(missing)}",
                location={"file": "manifest.json" if (self.target_dir / "manifest.json").is_file() else "SKILL.md"},
                evidence=f"Required fields missing: {missing}",
                remediation=f"在元数据中补充 {', '.join(missing)} 字段。",
            )

        # 检查 description 长度
        description = self._package_metadata.get("description", "")
        if description and len(description) < 10:
            self._add_finding(
                rule_id=rule_id,
                severity="info",
                category="metadata_quality",
                title="描述过短",
                description=f"包描述仅 {len(description)} 个字符，不足 10 个字符。",
                location={"file": "manifest.json" if (self.target_dir / "manifest.json").is_file() else "SKILL.md"},
                remediation="提供更详细的包描述（建议 10-200 字符）。",
            )

    # ------------------------------------------------------------------
    # 结构校验
    # ------------------------------------------------------------------

    def _sr_structure_check(self) -> None:
        """检查目录结构中是否有危险文件和缺失的关键文件。"""
        rule_id = "SR-010"  # 结构问题归类到元数据质量

        # 检查危险文件扩展名
        for fname in self.scanned_files:
            ext = Path(fname).suffix.lower()
            if ext in DANGEROUS_EXTENSIONS:
                self._add_finding(
                    rule_id=rule_id,
                    severity="medium",
                    category="metadata_quality",
                    title=f"可疑文件: {fname}",
                    description=f"发现二进制/可执行文件 '{fname}'（扩展名 {ext}），Skill 包不应包含编译产物。",
                    location={"file": fname},
                    evidence=f"Suspicious file extension: {ext}",
                    remediation="移除二进制文件，仅保留源代码和配置文件。",
                )

        # 检查关键文件
        if self._package_metadata:
            pkg_type = self._package_metadata.get("type", "")
            required = REQUIRED_FILES_BY_TYPE.get(pkg_type, [])
            for req_file in required:
                if not (self.target_dir / req_file).is_file():
                    self._add_finding(
                        rule_id=rule_id,
                        severity="medium",
                        category="metadata_quality",
                        title=f"缺少必要文件: {req_file}",
                        description=f"类型 '{pkg_type}' 的包缺少必要文件 '{req_file}'。",
                        location={"file": str(self.target_dir)},
                        remediation=f"添加 {req_file} 文件。",
                    )

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _add_finding(
        self,
        rule_id: str,
        severity: str,
        category: str,
        title: str,
        description: str,
        location: dict[str, Any] | None = None,
        evidence: str = "",
        remediation: str = "",
        cwe_id: str | None = None,
    ) -> None:
        """添加一条扫描发现。"""
        finding: dict[str, Any] = {
            "id": f"finding-{uuid.uuid4().hex[:8]}",
            "rule_id": rule_id,
            "severity": severity,
            "category": category,
            "title": title,
            "description": description,
        }
        if location:
            finding["location"] = location
        if evidence:
            finding["evidence"] = evidence
        if remediation:
            finding["remediation"] = remediation
        if cwe_id:
            finding["cwe_id"] = cwe_id

        self.findings.append(finding)

    def _build_report(self, start_time: datetime, duration_ms: int) -> dict[str, Any]:
        """生成符合 scan-report.schema.json 的完整报告。"""
        # 汇总
        severity_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for f in self.findings:
            sev = f.get("severity", "info")
            if sev in severity_counts:
                severity_counts[sev] += 1

        total = len(self.findings)
        pass_rate = max(0.0, 100.0 - (total * 5.0)) if total > 0 else 100.0
        pass_rate = round(min(pass_rate, 100.0), 1)

        # 包名和版本
        pkg_name = "unknown"
        pkg_version = "0.0.0"
        if self._package_metadata:
            pkg_name = self._package_metadata.get("name", "unknown")
            pkg_version = self._package_metadata.get("version", "0.0.0")

        # 元数据校验
        metadata_validation: dict[str, Any] = {"valid": True, "errors": []}
        if self._package_metadata:
            for field in ["name", "version", "description", "author", "license"]:
                if not self._package_metadata.get(field):
                    metadata_validation["valid"] = False
                    metadata_validation["errors"].append({
                        "field": field,
                        "message": f"Missing required field: {field}",
                    })
        else:
            metadata_validation["valid"] = False
            metadata_validation["errors"].append({
                "field": "*",
                "message": "No metadata file found (manifest.json / plugin.json / SKILL.md)",
            })

        # 结构检查
        structure_check: dict[str, Any] = {
            "valid": True,
            "missing_files": [],
            "extra_files": [],
        }
        if self._package_metadata:
            pkg_type = self._package_metadata.get("type", "")
            required = REQUIRED_FILES_BY_TYPE.get(pkg_type, [])
            for req_file in required:
                if not (self.target_dir / req_file).is_file():
                    structure_check["valid"] = False
                    structure_check["missing_files"].append(req_file)
        # 危险文件
        for fname in self.scanned_files:
            ext = Path(fname).suffix.lower()
            if ext in DANGEROUS_EXTENSIONS:
                structure_check["valid"] = False
                structure_check["extra_files"].append(fname)

        # 依赖检查（初版留空）
        dependency_check: dict[str, Any] = {
            "total_dependencies": 0,
            "known_vulnerabilities": 0,
            "unlocked_versions": 0,
            "suspicious_packages": [],
        }

        report: dict[str, Any] = {
            "scan_id": f"scan-{uuid.uuid4().hex[:12]}",
            "package_name": pkg_name,
            "version": pkg_version,
            "scanned_at": start_time.isoformat(),
            "scanner_version": "0.1.0",
            "duration_ms": duration_ms,
            "findings": self.findings,
            "summary": {
                "total": total,
                "critical": severity_counts["critical"],
                "high": severity_counts["high"],
                "medium": severity_counts["medium"],
                "low": severity_counts["low"],
                "info": severity_counts["info"],
                "pass_rate": pass_rate,
            },
            "metadata_validation": metadata_validation,
            "structure_check": structure_check,
            "dependency_check": dependency_check,
        }

        return report


# ---------------------------------------------------------------------------
# YAML Frontmatter 解析（纯标准库实现）
# ---------------------------------------------------------------------------


def _parse_frontmatter(content: str) -> dict[str, Any] | None:
    """解析 Markdown 文件的 YAML frontmatter (--- ... ---)。

    使用简单的逐行解析，避免引入 PyYAML 依赖。
    支持字符串、数字、布尔值、列表。
    """
    if not content.startswith("---"):
        return None

    end_idx = content.find("---", 3)
    if end_idx == -1:
        return None

    fm_text = content[3:end_idx].strip()
    result: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] = []

    for line in fm_text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # 列表项（以 - 开头）
        if stripped.startswith("- ") and current_key:
            current_list.append(stripped[2:].strip())
            continue

        # 保存之前的列表
        if current_key and current_list:
            result[current_key] = current_list
            current_list = []
            current_key = None

        # 新的 key: value
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            current_key = key

            if value.lower() == "true":
                result[key] = True
            elif value.lower() == "false":
                result[key] = False
            else:
                # 尝试数字
                try:
                    result[key] = int(value)
                except ValueError:
                    try:
                        result[key] = float(value)
                    except ValueError:
                        result[key] = value

    # 保存最后的列表
    if current_key and current_list:
        result[current_key] = current_list

    return result if result else None


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <target_directory> [--json]")
        print(f"Example: python {sys.argv[0]} examples/risky-packages/risky-executor")
        sys.exit(1)

    target = sys.argv[1]
    scanner = RiskScanner(target)
    report = scanner.scan()

    if "--json" in sys.argv:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        summary = report["summary"]
        print(f"\n  Scan Report: {report['package_name']} v{report['version']}")
        print(f"  {'─' * 50}")
        print(f"  Findings: {summary['total']} total")
        print(f"    Critical: {summary['critical']}")
        print(f"    High:     {summary['high']}")
        print(f"    Medium:   {summary['medium']}")
        print(f"    Low:      {summary['low']}")
        print(f"    Info:     {summary['info']}")
        print(f"  Pass Rate: {summary['pass_rate']}%")
        print(f"  Duration:  {report['duration_ms']}ms")
        print(f"  Scan ID:   {report['scan_id']}")
        print()

        if report["findings"]:
            print(f"  Detailed Findings:")
            for f in report["findings"]:
                sev_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}.get(f["severity"], "  ")
                print(f"    {sev_icon} [{f['severity'].upper()}] {f['title']}")
                loc = f.get("location", {})
                if loc.get("file"):
                    line_info = f":{loc['line']}" if loc.get("line") else ""
                    print(f"       📁 {loc['file']}{line_info}")
                print(f"       💡 {f.get('remediation', 'N/A')[:100]}")
                print()
