# THUQX‑智能传播技能套件 1.0

**真正自动生产内容 + 四平台一键发布**

清华大学新媒体研究中心 · AI 智能传播系统

---

## 支持平台

| 平台 | 脚本 | 功能 |
|------|------|------|
| Twitter / X | `twitter/cdp_tweet.py` | 自动发推 |
| 微博 | `weibo/cdp_weibo_publish.py` | 自动发微博 |
| 小红书 | `xiaohongshu/cdp_xhs_publish.py` | 自动发长文笔记 |
| 微信公众号 | `wechat/cdp_wechat_publish.py` | 自动保存草稿 |

## 项目结构

```
THUQX-智能传播技能套件1.0
├── README.md
├── scripts/
│   ├── generate_social_content_v4.py   # 多平台内容生成器
│   └── run_social_publish_v5.sh        # 四平台一键发布
├── twitter/
│   ├── cdp_tweet.py                    # Twitter CDP 自动发布
│   └── tweet.sh                        # Shell 入口
├── weibo/
│   ├── cdp_weibo_publish.py            # 微博 CDP 自动发布
│   └── run_weibo_publish.sh            # Shell 入口
├── xiaohongshu/
│   └── cdp_xhs_publish.py             # 小红书 CDP 自动发布
└── wechat/
    └── cdp_wechat_publish.py           # 微信公众号 CDP 草稿
```

## 快速开始

### 前置条件

1. macOS 系统，安装 Python 3.9+ 和 `websocket-client`：

```bash
pip3 install websocket-client
```

2. 以 CDP 模式启动 Chrome：

```bash
open -na "Google Chrome" --args \
  --remote-debugging-port=9222 \
  --user-data-dir=$HOME/chrome-cdp-profile
```

3. 在 Chrome 中登录以下平台：
   - https://x.com
   - https://weibo.com
   - https://creator.xiaohongshu.com
   - https://mp.weixin.qq.com

### 一键四平台发布

```bash
bash scripts/run_social_publish_v5.sh "AI认知债务"
```

系统自动执行：

```
生成四平台定制内容
  ↓
Twitter 发推
  ↓
微博 发布
  ↓
小红书 发长文
  ↓
微信公众号 保存草稿
```

### 单平台发布

```bash
# Twitter
python3 twitter/cdp_tweet.py "Your tweet content"

# 微博
python3 weibo/cdp_weibo_publish.py "微博内容"

# 小红书
python3 xiaohongshu/cdp_xhs_publish.py "标题" "正文内容"

# 微信公众号（保存草稿，不会群发）
python3 wechat/cdp_wechat_publish.py "标题" "正文内容" --author "大可舆评"
```

## 技术原理

通过 Chrome DevTools Protocol (CDP) 直接操控浏览器，模拟真实用户操作：

- 使用 WebSocket 连接 Chrome 的调试端口（9222）
- 通过 `Runtime.evaluate` 执行 JavaScript 操作页面 DOM
- 通过 `Input.insertText` 模拟键盘输入
- 自动处理 SPA 路由、iframe 编辑器、确认弹窗等场景

## 自恢复机制

- CDP 断开时自动重启 Chrome
- 发布失败自动重试
- 确认弹窗自动点击

## License

MIT

---

*THUQX‑智能传播技能套件 · 清华大学新媒体研究中心*
