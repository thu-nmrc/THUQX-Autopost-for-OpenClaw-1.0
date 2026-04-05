#!/bin/bash
# THUQX 智能传播技能套件 — 四平台一键发布 v5
# 用法: bash scripts/run_social_publish_v5.sh "AI认知债务"
set -o pipefail

TOPIC="${1:-AI认知债务}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
CDP_PORT="${OPENCLAW_CDP_PORT:-9222}"

# ── CDP 自检 & 自动启动 ─────────────────────────────
ensure_cdp() {
  if curl -s --max-time 2 "http://127.0.0.1:${CDP_PORT}/json" >/dev/null 2>&1; then
    echo "[CDP] Chrome DevTools Protocol OK (port ${CDP_PORT})"
    return 0
  fi
  echo "[CDP] Chrome not reachable, launching..."
  open -na "Google Chrome" --args \
    --remote-debugging-port="${CDP_PORT}" \
    --user-data-dir="$HOME/chrome-cdp-profile" 2>/dev/null
  for i in $(seq 1 15); do
    sleep 2
    if curl -s --max-time 2 "http://127.0.0.1:${CDP_PORT}/json" >/dev/null 2>&1; then
      echo "[CDP] Chrome started on port ${CDP_PORT}"
      return 0
    fi
  done
  echo "[CDP] ERROR: Could not start Chrome with CDP. Aborting." >&2
  exit 1
}

ensure_cdp

# ── 生成内容 ─────────────────────────────────────────
echo "Generating content for topic: ${TOPIC}"
CONTENT=$(python3 "$SCRIPT_DIR/generate_social_content_v4.py" "$TOPIC")
if [ -z "$CONTENT" ]; then
  echo "ERROR: Content generation failed." >&2
  exit 1
fi

extract() { echo "$CONTENT" | python3 -c "import sys,json;print(json.load(sys.stdin)['$1'])"; }

TW="$(extract twitter)"
WB="$(extract weibo)"
XT="$(extract xhs_title)"
XB="$(extract xhs_body)"
WT="$(extract wechat_title)"
WBODY="$(extract wechat_body)"

# ── 四平台并行发布 ───────────────────────────────────
echo ""
echo "========== THUQX 智能传播 =========="
echo "Twitter / 微博 / 小红书 / 微信公众号"
echo "====================================="
echo ""

echo "[1/4] Publishing Twitter..."
python3 "$ROOT_DIR/twitter/cdp_tweet.py" "$TW" 2>&1 | sed 's/^/  [Twitter] /' &
PID_TW=$!

echo "[2/4] Publishing 微博..."
python3 "$ROOT_DIR/weibo/cdp_weibo_publish.py" "$WB" 2>&1 | sed 's/^/  [Weibo] /' &
PID_WB=$!

echo "[3/4] Publishing 小红书..."
python3 "$ROOT_DIR/xiaohongshu/cdp_xhs_publish.py" "$XT" "$XB" 2>&1 | sed 's/^/  [XHS] /' &
PID_XHS=$!

echo "[4/4] Publishing 微信公众号 (草稿)..."
python3 "$ROOT_DIR/wechat/cdp_wechat_publish.py" "$WT" "$WBODY" 2>&1 | sed 's/^/  [WeChat] /' &
PID_WC=$!

# ── 等待完成 ─────────────────────────────────────────
FAIL=0
wait $PID_TW  || FAIL=$((FAIL+1))
wait $PID_WB  || FAIL=$((FAIL+1))
wait $PID_XHS || FAIL=$((FAIL+1))
wait $PID_WC  || FAIL=$((FAIL+1))

echo ""
echo "====================================="
if [ "$FAIL" -eq 0 ]; then
  echo "All 4 platforms published successfully."
else
  echo "WARNING: $FAIL platform(s) may need manual check."
fi
echo "====================================="
