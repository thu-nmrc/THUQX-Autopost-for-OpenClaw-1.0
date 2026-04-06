#!/bin/bash
# THUQX Autopost for OpenClaw 1.0 — 四平台一键发布
# 用法: bash scripts/run_social_publish_v5.sh "主题"
# 顺序发布（同一 CDP 浏览器下并行会争抢输入焦点）
set -o pipefail

TOPIC="${1:-AI认知债务}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
CDP_PORT="${OPENCLAW_CDP_PORT:-9222}"

ensure_cdp() {
  if curl -s --max-time 2 "http://127.0.0.1:${CDP_PORT}/json" >/dev/null 2>&1; then
    echo "[CDP] OK (port ${CDP_PORT})"
    return 0
  fi
  echo "[CDP] Chrome not reachable, launching..."
  if command -v open >/dev/null 2>&1; then
    open -na "Google Chrome" --args \
      --remote-debugging-port="${CDP_PORT}" \
      --user-data-dir="${HOME}/chrome-cdp-profile" \
      --remote-allow-origins="*" \
      --no-first-run \
      "https://x.com" \
      "https://weibo.com" \
      "https://creator.xiaohongshu.com/publish/publish?source=official&from=menu&target=article" \
      "https://mp.weixin.qq.com" 2>/dev/null || true
  elif command -v google-chrome >/dev/null 2>&1; then
    google-chrome --remote-debugging-port="${CDP_PORT}" \
      --user-data-dir="${HOME}/chrome-cdp-profile" \
      --remote-allow-origins="*" \
      --no-first-run \
      "https://x.com" "https://weibo.com" \
      "https://creator.xiaohongshu.com/publish/publish?source=official&from=menu&target=article" \
      "https://mp.weixin.qq.com" 2>/dev/null &
  elif command -v chromium >/dev/null 2>&1; then
    chromium --remote-debugging-port="${CDP_PORT}" \
      --user-data-dir="${HOME}/chrome-cdp-profile" \
      --remote-allow-origins="*" \
      --no-first-run \
      "https://x.com" "https://weibo.com" \
      "https://creator.xiaohongshu.com/publish/publish?source=official&from=menu&target=article" \
      "https://mp.weixin.qq.com" 2>/dev/null &
  else
    echo "[CDP] ERROR: Install Chrome or start CDP manually on port ${CDP_PORT}." >&2
    exit 1
  fi
  for _ in $(seq 1 15); do
    sleep 2
    if curl -s --max-time 2 "http://127.0.0.1:${CDP_PORT}/json" >/dev/null 2>&1; then
      echo "[CDP] Chrome started on port ${CDP_PORT}"
      return 0
    fi
  done
  echo "[CDP] ERROR: Could not start Chrome with CDP." >&2
  exit 1
}

ensure_cdp

if [ "${SKIP_CONTENT_GEN:-0}" = "1" ] && [ -n "${THUQX_CONTENT_JSON}" ] && [ -f "${THUQX_CONTENT_JSON}" ]; then
  CONTENT="$(cat "${THUQX_CONTENT_JSON}")"
else
  echo "Generating content for topic: ${TOPIC}"
  CONTENT="$(python3 "$SCRIPT_DIR/generate_content.py" "$TOPIC")"
fi

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

echo ""
echo "========== THUQX 四平台顺序发布 =========="
echo "Twitter → 微博 → 小红书 → 微信公众号(草稿)"
echo "========================================="
echo ""

FAIL=0

echo "[1/4] Twitter..."
bash "$ROOT_DIR/twitter/tweet.sh" "$TW" 2>&1 | sed 's/^/  [Twitter] /'
[ "${PIPESTATUS[0]}" -ne 0 ] && FAIL=$((FAIL + 1))

echo "[2/4] Weibo..."
bash "$ROOT_DIR/weibo/run_weibo_publish.sh" "$WB" 2>&1 | sed 's/^/  [Weibo] /'
[ "${PIPESTATUS[0]}" -ne 0 ] && FAIL=$((FAIL + 1))

echo "[3/4] Xiaohongshu..."
python3 "$ROOT_DIR/xiaohongshu/cdp_xhs_publish.py" "$XT" "$XB" 2>&1 | sed 's/^/  [XHS] /'
[ "${PIPESTATUS[0]}" -ne 0 ] && FAIL=$((FAIL + 1))

echo "[4/4] WeChat (draft)..."
python3 "$ROOT_DIR/wechat/cdp_wechat_publish.py" "$WT" "$WBODY" 2>&1 | sed 's/^/  [WeChat] /'
[ "${PIPESTATUS[0]}" -ne 0 ] && FAIL=$((FAIL + 1))

echo ""
echo "========================================="
if [ "$FAIL" -eq 0 ]; then
  echo "All 4 platforms finished successfully."
else
  echo "WARNING: $FAIL platform(s) may need a manual check."
fi
echo "========================================="

[ "$FAIL" -gt 0 ] && exit 1
exit 0
