# Claude 环境检查与清理

> 普通 Mac 用户不需要 Codex，不需要自己打开“终端”，也不需要会写代码。

## 普通用户：只做这 3 步

1. 点击 GitHub 页面右上方的 **Code → Download ZIP**
2. 双击下载的 ZIP 文件进行解压
3. 打开解压后的文件夹，双击 **`双击启动.command`**

出现菜单后，直接按回车就会运行推荐的“一键检查”。一键检查是只读的，**不会删除或修改任何 Claude / 浏览器配置**，只会保存一份检查报告。

```text
==================================
  Claude 环境检查与清理
==================================
  [1] 一键检查（推荐，只读）
  [2] 安全清理（缓存和日志）
  [3] 深度清理（会先备份）
  [4] 查看报告
  [0] 退出
```

### 如果 Mac 不让打开

第一次双击时，macOS 可能会进行安全提示。请对 **`双击启动.command`** 点击右键，选择“打开”，再确认一次。

如果提示缺少 Python 3 或版本太旧，按回车会自动打开 Python 官方下载页。安装 Python 3.10 或更新版本后，重新双击启动文件即可。

## 这些选项会做什么

- **一键检查**：复用 `scripts/audit_claude_env.py` 和 `scripts/audit_network_env.py`，只读检查本机配置、应用残留、CC Switch、本地代理、DNS 和网络环境。不访问外部 IP 检测服务。
- **安全清理**：处理 Claude / CC Switch 的缓存、日志和 telemetry 目录。
- **深度清理**：额外处理 Claude / CC Switch 应用、应用数据、凭据文件、偏好设置、启动项和 Anthropic 浏览器通信清单。
- **查看报告**：打开最近一次只读检查报告。

清理前，工具会先列出将处理的每一项内容，然后要求两次确认。所有内容都只会移到备份，不会永久删除。

## 备份和报告在哪里

工具只根据当前用户的 HOME 目录生成路径，没有硬编码用户名。

```text
~/Backups/claude-env-cleanup/        可恢复的清理备份
~/Documents/Claude环境清理报告/  最近一次检查报告
```

每个备份文件夹都有 `manifest.json`，记录原位置和备份位置，方便恢复。

## 安全边界

- 菜单默认项永远是只读检查。
- 清理必须先展示目标，再经过两次明确确认。
- 工具不会删除浏览器 Cookie、Local Storage、IndexedDB、整个浏览器档案或系统字体。
- 工具不会处理与 Claude / CC Switch 无关的应用、代理、配置或开发工具。
- `~/.claude/projects` 和 `~/.claude/skills` 等用户项目数据不在自动清理范围内。
- 脚本不会输出 token、API key、OAuth 凭据或 Cookie 原文。
- `/Applications` 中需要管理员权限的项目无法处理时，会安全跳过并告知用户。

## 高级用户 / Codex（可选）

Codex 不是普通流程的依赖。`SKILL.md` 仅用于让 Codex 调用同一套独立程序。

```bash
python3 cleanup.py --check
python3 cleanup.py --safe-clean --dry-run
python3 cleanup.py --deep-clean --dry-run
```

只有去掉 `--dry-run` 才会进入两次确认的实际清理流程。

## 开发与测试

项目只使用 Python 3 标准库，无需安装第三方依赖。

```bash
python3 -m unittest discover -s tests -v
python3 cleanup.py --deep-clean --dry-run
```

---

English summary: download the ZIP, extract it, and double-click `双击启动.command`. The default action is a read-only audit. Cleanup lists every target, asks for two confirmations, and moves items into a timestamped backup under the current user's HOME. Codex is optional.
