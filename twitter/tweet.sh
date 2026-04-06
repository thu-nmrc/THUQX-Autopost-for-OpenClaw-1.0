#!/bin/bash
# Twitter 运营入口 — 调用 CDP 脚本
# 用法: bash tweet.sh "tweet content" [url]
set -o pipefail

CONTENT="${1:?Error: tweet content required}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

python3 "$SCRIPT_DIR/cdp_tweet.py" "$CONTENT" 2>&1
