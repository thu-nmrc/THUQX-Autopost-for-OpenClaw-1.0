#!/bin/bash
# THUQX Social Ops for OpenClaw 1.0 — 四平台一键运营
# 用法: bash scripts/run_social_ops_v5.sh "主题"
# 环境变量: OPENCLAW_CDP_PORT, THUQX_PLATFORM_PAUSE（默认 2）, SKIP_CONTENT_GEN + THUQX_CONTENT_JSON
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/_thuqx_cdp_common.sh"

PAUSE="${THUQX_PLATFORM_PAUSE:-2}"
TOPIC="${1:-AI认知债务}"

thuqx_ensure_cdp || exit 1

if [ "${SKIP_CONTENT_GEN:-0}" = "1" ] && [ -n "${THUQX_CONTENT_JSON:-}" ] && [ -f "${THUQX_CONTENT_JSON}" ]; then
  echo "Using pre-generated JSON: ${THUQX_CONTENT_JSON}"
  CONTENT="$(cat "${THUQX_CONTENT_JSON}")"
else
  echo "Generating content for topic: ${TOPIC}"
  CONTENT="$(python3 "$SCRIPT_DIR/generate_content.py" "$TOPIC")"
fi

if [ -z "$CONTENT" ]; then
  echo "ERROR: Content generation failed." >&2
  exit 1
fi

if ! echo "$CONTENT" | python3 -c "
import json, sys
keys = ('twitter','weibo','xhs_title','xhs_body','wechat_title','wechat_body')
d = json.load(sys.stdin)
missing = [k for k in keys if k not in d or not str(d[k]).strip()]
sys.exit(1 if missing else 0)
" 2>/dev/null; then
  echo "ERROR: JSON missing required keys or empty values." >&2
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
echo "========== THUQX 四平台顺序运营 =========="
echo "Twitter → 微博 → 小红书 → 微信公众号(草稿)"
echo "========================================="
echo ""

FAIL=0

echo "[1/4] Twitter Ops..."
bash "$ROOT_DIR/twitter/tweet.sh" "$TW" 2>&1 | sed 's/^/  [Twitter] /'
[ "${PIPESTATUS[0]}" -ne 0 ] && FAIL=$((FAIL + 1))
sleep "$PAUSE"

echo "[2/4] Weibo Ops..."
bash "$ROOT_DIR/weibo/run_weibo_ops.sh" "$WB" 2>&1 | sed 's/^/  [Weibo] /'
[ "${PIPESTATUS[0]}" -ne 0 ] && FAIL=$((FAIL + 1))
sleep "$PAUSE"

echo "[3/4] Xiaohongshu Ops..."
python3 "$ROOT_DIR/xiaohongshu/cdp_xhs_ops.py" "$XT" "$XB" 2>&1 | sed 's/^/  [XHS] /'
[ "${PIPESTATUS[0]}" -ne 0 ] && FAIL=$((FAIL + 1))
sleep "$PAUSE"

echo "[4/4] WeChat Ops (draft)..."
python3 "$ROOT_DIR/wechat/cdp_wechat_ops.py" "$WT" "$WBODY" 2>&1 | sed 's/^/  [WeChat] /'
[ "${PIPESTATUS[0]}" -ne 0 ] && FAIL=$((FAIL + 1))

echo ""
echo "========================================="
if [ "$FAIL" -eq 0 ]; then
  echo "All 4 platforms Ops finished successfully."
else
  echo "WARNING: $FAIL platform(s) may need a manual check."
fi
echo "========================================="

[ "$FAIL" -gt 0 ] && exit 1
exit 0
