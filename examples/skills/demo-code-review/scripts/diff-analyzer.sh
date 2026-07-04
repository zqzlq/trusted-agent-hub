#!/bin/bash
# diff-analyzer.sh — 分析 git diff 输出，生成变更摘要

set -euo pipefail

TARGET_BRANCH="${1:-main}"
OUTPUT_FILE="${2:-diff-summary.txt}"

echo "=== Diff Summary against $TARGET_BRANCH ===" > "$OUTPUT_FILE"
echo "Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# 变更统计
git diff --stat "$TARGET_BRANCH" >> "$OUTPUT_FILE" 2>/dev/null || echo "(no changes)" >> "$OUTPUT_FILE"

echo "" >> "$OUTPUT_FILE"
echo "=== Changed Files ===" >> "$OUTPUT_FILE"
git diff --name-only "$TARGET_BRANCH" >> "$OUTPUT_FILE" 2>/dev/null || echo "(none)" >> "$OUTPUT_FILE"

echo "Diff summary written to $OUTPUT_FILE"
