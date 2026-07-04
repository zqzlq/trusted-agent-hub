"""
demo-filesystem MCP Server
一个简单的文件系统浏览 MCP Server，仅提供只读文件列表和内容读取。
仅供示例和测试用途。
"""

import os
import json
import sys
from pathlib import Path


ALLOWED_DIRS = [os.path.expanduser("~"), os.getcwd()]


def is_path_allowed(target_path: str) -> bool:
    """检查路径是否在允许的目录范围内"""
    resolved = os.path.realpath(os.path.expanduser(target_path))
    for allowed in ALLOWED_DIRS:
        allowed_resolved = os.path.realpath(os.path.expanduser(allowed))
        if resolved.startswith(allowed_resolved):
            return True
    return False


def list_directory(path: str = ".") -> list[dict]:
    """列出目录内容"""
    full_path = os.path.expanduser(path)
    if not is_path_allowed(full_path):
        return [{"error": f"Access denied: {path}"}]

    try:
        entries = []
        for entry in sorted(os.listdir(full_path)):
            entry_path = os.path.join(full_path, entry)
            entries.append({
                "name": entry,
                "type": "directory" if os.path.isdir(entry_path) else "file",
                "size": os.path.getsize(entry_path) if os.path.isfile(entry_path) else None,
                "modified": os.path.getmtime(entry_path)
            })
        return entries
    except PermissionError:
        return [{"error": f"Permission denied: {path}"}]
    except FileNotFoundError:
        return [{"error": f"Not found: {path}"}]


def read_file(path: str, max_lines: int = 200) -> dict:
    """读取文件内容（仅文本文件）"""
    full_path = os.path.expanduser(path)
    if not is_path_allowed(full_path):
        return {"error": f"Access denied: {path}"}

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"... (truncated after {max_lines} lines)")
                    break
                lines.append(line.rstrip())
            return {"path": path, "lines": len(lines), "content": "\n".join(lines)}
    except UnicodeDecodeError:
        return {"error": f"Binary file: {path}"}
    except FileNotFoundError:
        return {"error": f"Not found: {path}"}
    except PermissionError:
        return {"error": f"Permission denied: {path}"}


def handle_request(request: dict) -> dict:
    """处理 MCP 请求（简化版）"""
    method = request.get("method")
    params = request.get("params", {})

    if method == "tools/list":
        return {
            "tools": [
                {"name": "list_directory", "description": "列出目录内容", "inputSchema": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "default": "."}}
                }},
                {"name": "read_file", "description": "读取文件内容（只读，最多 200 行）", "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "max_lines": {"type": "integer", "default": 200}
                    },
                    "required": ["path"]
                }}
            ]
        }

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "list_directory":
            return {"content": [{"type": "text", "text": json.dumps(
                list_directory(arguments.get("path", ".")), indent=2
            )}]}

        if tool_name == "read_file":
            return {"content": [{"type": "text", "text": json.dumps(
                read_file(arguments["path"], arguments.get("max_lines", 200)), indent=2
            )}]}

    return {"error": f"Unknown method: {method}"}


if __name__ == "__main__":
    # 从 stdin 读取 JSON 请求，打印 JSON 响应（stdio transport）
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            response = handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON"}), flush=True)
