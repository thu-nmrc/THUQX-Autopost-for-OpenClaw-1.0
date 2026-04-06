# OpenClaw 集成说明

**上游仓库：** [thu-nmrc/THUQX-Autops-for-OpenClaw-0.5](https://github.com/thu-nmrc/THUQX-Autops-for-OpenClaw-0.5)（THUQX AutoOps for OpenClaw **0.5**）

本仓库脚本与本地 **OpenClaw skills** 目录保持同一逻辑，便于双向同步。

## 推荐映射（复制到 `~/.openclaw/workspace/skills/`）

| 本仓库路径 | OpenClaw skill 目录 |
|------------|---------------------|
| `scripts/_thuqx_cdp_common.sh` | `zeelin-social-autopublisher/scripts/_thuqx_cdp_common.sh` |
| `scripts/generate_content.py` | `zeelin-social-autopublisher/scripts/generate_content.py` |
| `scripts/run_social_ops_v5.sh` | `zeelin-social-autopublisher/scripts/run_social_ops_v5.sh` |
| `twitter/*` | `zeelin-twitter-web-autopost/scripts/` |
| `weibo/*` | `zeelin-weibo-autopost/scripts/` |
| `xiaohongshu/cdp_xhs_ops.py` | `zeelin-xiaohongshu-autopost/scripts/cdp_xhs_ops.py`（可与现有 `cdp_xhs_publish_v5.py` 并存或覆盖） |
| `wechat/cdp_wechat_ops.py` | `zeelin-wechat-autopost/scripts/cdp_wechat_ops.py`（可与 `cdp_wechat_publish_v10.py` 并存或覆盖） |

## OpenClaw 一键命令

```bash
bash "$HOME/.openclaw/workspace/skills/zeelin-social-autopublisher/scripts/run_social_ops_v5.sh" "主题"
```

## 设计要点

1. **顺序运营（Ops）**：同一 Chrome CDP 实例上并行多脚本会导致 `Input.insertText` 与焦点错乱，编排脚本必须为顺序执行。
2. **Chrome 参数**：需 `--user-data-dir` 与 `--remote-allow-origins=*`，否则新版 Chrome 可能不开放 CDP 或拒绝 WebSocket。
3. **小红书**：长文路径为「写长文 → 新的创作 → 一键排版 → 下一步 → 平台提交」；勿点击侧边栏「发布笔记」导航项。

详见各目录下脚本注释与 `openclaw/zeelin-social-autopublisher/SKILL.md`。
