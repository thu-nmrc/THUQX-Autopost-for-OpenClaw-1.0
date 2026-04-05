#!/bin/bash

# Weibo CDP publisher wrapper
# Usage:
# run_weibo_publish.sh "content"

CONTENT="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -z "$CONTENT" ]; then
  echo "Usage: run_weibo_publish.sh \"content\""
  exit 1
fi

python3 "$SCRIPT_DIR/cdp_weibo_publish.py" "$CONTENT"
