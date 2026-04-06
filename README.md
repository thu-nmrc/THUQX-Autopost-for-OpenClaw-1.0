# THUQX Social Ops for OpenClaw 1.0

**AI 多平台文案生成 + 四平台顺序自动运营（CDP）**

清华大学新媒体研究中心 · 智能传播工具链

---

## 支持平台

| 平台 | 脚本 | 功能 |
|------|------|------|
| Twitter / X | `twitter/cdp_tweet.py` | 自动发推（Ops） |
| 微博 | `weibo/cdp_weibo_ops.py` | 自动发微博（Ops） |
| 小红书 | `xiaohongshu/cdp_xhs_ops.py` | 长文笔记（写长文 → 排版 → 平台侧提交） |
| 微信公众号 | `wechat/cdp_wechat_ops.py` | 保存草稿（不群发） |

## 项目结构

```
├── README.md
├── OPENCLAW.md
├── scripts/
│   ├── _thuqx_cdp_common.sh
│   ├── generate_content.py
│   ├── generate_social_content_v4.py
│   ├── run_social_ops_v5.sh           # 四平台一键顺序运营（推荐）
│   └── run_social_publish_v5.sh       # 兼容入口，转调 run_social_ops_v5.sh
├── twitter/
│   ├── cdp_tweet.py
│   └── tweet.sh
├── weibo/
│   ├── cdp_weibo_ops.py
│   ├── run_weibo_ops.sh
│   └── run_weibo_publish.sh           # 兼容入口
├── xiaohongshu/
│   └── cdp_xhs_ops.py
└── wechat/
    └── cdp_wechat_ops.py
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

在以上标签页中完成各平台登录。`run_social_ops_v5.sh` 也会在 CDP 不可用时尝试按上述参数自动拉起 Chrome（macOS / Linux）。

### 一键四平台（推荐）

```bash
bash scripts/run_social_ops_v5.sh "AI认知债务"
```

可选：`THUQX_PLATFORM_PAUSE=3` 加大平台间间隔（秒，默认 2），网络或 SPA 慢时更稳。

执行顺序（**顺序运营**，避免多脚本争抢同一浏览器焦点）：

```
generate_content.py 生成四平台 JSON
  → Twitter Ops
  → 微博 Ops
  → 小红书 Ops
  → 微信公众号（草稿 Ops）
```

### 单平台

```bash
python3 twitter/cdp_tweet.py "推文内容"
python3 weibo/cdp_weibo_ops.py "微博正文"
python3 xiaohongshu/cdp_xhs_ops.py "标题" "正文"
python3 wechat/cdp_wechat_ops.py "标题" "正文"
```

## OpenClaw

若使用 **OpenClaw**，请将脚本同步到 `~/.openclaw/workspace/skills/` 下各 `zeelin-*` 目录，一键入口见 **`OPENCLAW.md`** 与 **`openclaw/zeelin-social-autopublisher/SKILL.md`**。

## 技术说明

- Chrome DevTools Protocol（WebSocket + `Runtime.evaluate` / `Input.insertText` 等）
- 小红书：自动化会点击页面上的「发布」等**平台原生控件**（文案仍为平台 UI）；请勿误点侧边栏「发布笔记」导航。
- Twitter：使用 `document.execCommand('insertText')` 以触发 React 编辑器状态，避免发帖按钮一直禁用。

## License

MIT

---

*THUQX · 清华大学新媒体研究中心*
