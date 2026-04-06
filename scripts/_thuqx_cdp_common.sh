# shellcheck shell=bash
# THUQX — CDP 自检与启动（由 run_social_ops_v5.sh source）

thuqx_ensure_cdp() {
  local port="${OPENCLAW_CDP_PORT:-9222}"
  if curl -s --max-time 2 "http://127.0.0.1:${port}/json" >/dev/null 2>&1; then
    echo "[CDP] OK (port ${port})"
    return 0
  fi
  echo "[CDP] Chrome not reachable, launching..."
  if command -v open >/dev/null 2>&1; then
    open -na "Google Chrome" --args \
      --remote-debugging-port="${port}" \
      --user-data-dir="${HOME}/chrome-cdp-profile" \
      --remote-allow-origins="*" \
      --no-first-run \
      "https://x.com" \
      "https://weibo.com" \
      "https://creator.xiaohongshu.com/publish/publish?source=official&from=menu&target=article" \
      "https://mp.weixin.qq.com" 2>/dev/null || true
  elif command -v google-chrome >/dev/null 2>&1; then
    google-chrome --remote-debugging-port="${port}" \
      --user-data-dir="${HOME}/chrome-cdp-profile" \
      --remote-allow-origins="*" \
      --no-first-run \
      "https://x.com" "https://weibo.com" \
      "https://creator.xiaohongshu.com/publish/publish?source=official&from=menu&target=article" \
      "https://mp.weixin.qq.com" 2>/dev/null &
  elif command -v chromium >/dev/null 2>&1; then
    chromium --remote-debugging-port="${port}" \
      --user-data-dir="${HOME}/chrome-cdp-profile" \
      --remote-allow-origins="*" \
      --no-first-run \
      "https://x.com" "https://weibo.com" \
      "https://creator.xiaohongshu.com/publish/publish?source=official&from=menu&target=article" \
      "https://mp.weixin.qq.com" 2>/dev/null &
  else
    echo "[CDP] ERROR: Install Chrome or start CDP on port ${port}." >&2
    echo "       Chrome 需: --user-data-dir 与 --remote-allow-origins=*" >&2
    return 1
  fi
  local i
  for i in $(seq 1 15); do
    sleep 2
    if curl -s --max-time 2 "http://127.0.0.1:${port}/json" >/dev/null 2>&1; then
      echo "[CDP] Chrome started on port ${port}"
      return 0
    fi
  done
  echo "[CDP] ERROR: Could not start Chrome with CDP." >&2
  return 1
}
