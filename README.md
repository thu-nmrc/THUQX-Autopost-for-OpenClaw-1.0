# THUQX Autopost for OpenClaw 1.0

**AI 多平台文案生成 + 四平台顺序自动发布（CDP）**

清华大学新媒体研究中心 · 智能传播工具链

---

## 支持平台

| 平台 | 脚本 | 功能 |
|------|------|------|
| Twitter / X | `twitter/cdp_tweet.py` | 自动发推 |
| 微博 | `weibo/cdp_weibo_publish.py` | 自动发微博 |
| 小红书 | `xiaohongshu/cdp_xhs_publish.py` | 长文笔记（写长文 → 排版 → 发布） |
| 微信公众号 | `wechat/cdp_wechat_publish.py` | 保存草稿（不群发） |

## 项目结构

```
├── README.md
├── OPENCLAW.md                         # 与 OpenClaw skills 目录的映射说明
├── scripts/
│   ├── generate_content.py             # 多平台内容生成（JSON stdout）
│   ├── generate_social_content_v4.py   # 兼容入口，转调 generate_content.py
│   └── run_social_publish_v5.sh        # 四平台一键顺序发布 + CDP 自检
├── twitter/
│   ├── cdp_tweet.py
│   └── tweet.sh
├── weibo/
│   ├── cdp_weibo_publish.py
│   └── run_weibo_publish.sh
├── xiaohongshu/
│   └── cdp_xhs_publish.py
└── wechat/
    └── cdp_wechat_publish.py
```

## 快速开始

### 依赖

```bash
pip3 install websocket-client
```

### Chrome CDP（新版 Chrome 必看）

必须指定独立用户目录，并允许 DevTools 来源，否则可能无法连接 WebSocket：

**macOS**

```bash
open -na "Google Chrome" --args \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-cdp-profile" \
  --remote-allow-origins="*" \
  "https://x.com" \
  "https://weibo.com" \
  "https://creator.xiaohongshu.com/publish/publish?source=official&from=menu&target=article" \
  "https://mp.weixin.qq.com"
```

在以上标签页中完成各平台登录。`run_social_publish_v5.sh` 也会在 CDP 不可用时尝试按上述参数自动拉起 Chrome（macOS / Linux）。

### 一键四平台（推荐）

```bash
bash scripts/run_social_publish_v5.sh "AI认知债务"
```

执行顺序（**顺序发布**，避免多脚本争抢同一浏览器焦点）：

```
generate_content.py 生成四平台 JSON
  → Twitter
  → 微博
  → 小红书
  → 微信公众号（草稿）
```

### 单平台

```bash
python3 twitter/cdp_tweet.py "推文内容"
python3 weibo/cdp_weibo_publish.py "微博正文"
python3 xiaohongshu/cdp_xhs_publish.py "标题" "正文"
python3 wechat/cdp_wechat_publish.py "标题" "正文"
```

## OpenClaw

若使用 **OpenClaw**，请将脚本同步到 `~/.openclaw/workspace/skills/` 下各 `zeelin-*` 目录，一键入口见 **`OPENCLAW.md`** 与 skill **`zeelin-social-autopublisher/SKILL.md`**（随技能包分发）。

## 技术说明

- Chrome DevTools Protocol（WebSocket + `Runtime.evaluate` / `Input.insertText` 等）
- 小红书 SPA：长文编辑器 → 一键排版 → 下一步 → 发布；请勿误点侧边栏「发布笔记」导航
- Twitter：使用 `document.execCommand('insertText')` 以触发 React 编辑器状态，避免发帖按钮一直禁用

## License

MIT

---

*THUQX · 清华大学新媒体研究中心*
