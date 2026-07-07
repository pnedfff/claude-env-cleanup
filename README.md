# Claude Env Cleanup Skill

> 中文说明在前，English follows.

## 中文

`claude-env-cleanup` 是一个 Codex skill，用于审计和清理 macOS 本机上的 Claude / CC Switch / coding-agent 环境残留。

它的默认原则是：**先只读审计，明确要求清理时才改动；改动前先备份；不打印密钥内容。**

### 适用场景

- 检查 Claude Code / Claude Desktop 是否还有残留
- 清理 Claude App、Claude PWA、Claude Code URL Handler、Chrome Native Messaging bridge
- 排查 `ANTHROPIC_*`、`127.0.0.1:15721`、CC Switch / 302AI / GLM 路由残留
- 删除 CC Switch app、cask、`~/.cc-switch` 状态
- 监测 Claude 网络环境：IP 纯净度、DNS 泄露、WebRTC 泄露、节点地区稳定性
- Claude 账号被封后的三步自查：清浏览器 Cookie/站点数据、删除 CC Switch、检查 Claude Code 终端和桌面 App
- 检查 browser fingerprint 相关信号，例如系统时区、`Intl` locale、浏览器语言、中文字体探测
- 审计 coding-agent 配置中的路由覆盖、请求改写、权限绕过和高风险本地网关设置

### 安装

把这个仓库 clone 到 Codex skills 目录：

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/pnedfff/claude-env-cleanup.git ~/.codex/skills/claude-env-cleanup
```

重启 Codex 后即可通过 `claude-env-cleanup` skill 触发。

### 只读审计

可以直接运行内置审计脚本：

```bash
python3 ~/.codex/skills/claude-env-cleanup/scripts/audit_claude_env.py
```

脚本只输出安全摘要，例如配置文件是否存在、是否发现 key 名称、路由标记、进程/端口/浏览器桥接状态；不会打印 token、API key、OAuth refresh token 等原始值。

网络环境审计可以运行：

```bash
python3 ~/.codex/skills/claude-env-cleanup/scripts/audit_network_env.py
```

默认只做本机代理、DNS、路由、浏览器语言等只读检查。需要公网 IP / Claude 连通性时再加 `--external`。人工复核默认只使用 3 个核心网站：`ip.net.coffee/claude`、`ippure.com/claude`、`iplark.com`。

账号被封后的自查模式：

```bash
python3 ~/.codex/skills/claude-env-cleanup/scripts/audit_network_env.py --post-ban
```

这个模式会列出浏览器站点数据的手动清理目标、醒目的手动动作提醒，以及文章里的 5 个复核网站：`ip.net.coffee/claude`、`iplark.com`、`net.coffee`、`ippure.com`、`cc.mastersgo.cc`。

### 安全边界

- 默认不删除任何东西。
- 浏览器 Cookie、Local Storage、IndexedDB、扩展和整份浏览器 profile 不会自动删除；这些属于高影响动作，必须手动处理或明确授权后再做。
- 删除或修改前应创建时间戳备份，通常放在 `/Users/<you>/Backups/`。
- 默认保留 Teamo、`~/.teamo`、`~/.claude/projects`。
- 默认保留 `com.claude-to-im.bridge`，它可能是 Codex/IM 接入桥，不等于官方 Claude 残留。
- 不要删除 macOS 系统字体。PingFang、Hiragino、STHeiti、Songti/STSong 等系统字体可能仍会被 canvas 字体探测检测到。
- ClashX 等通用代理不要和 Claude 专用 `127.0.0.1:15721` 路由混在一起清理。

### 仓库结构

```text
.
├── SKILL.md
├── agents/
│   └── openai.yaml
└── scripts/
    ├── audit_claude_env.py
    └── audit_network_env.py
```

## English

`claude-env-cleanup` is a Codex skill for auditing and cleaning local Claude / CC Switch / coding-agent residue on macOS.

Its default posture is: **audit first, mutate only when explicitly asked, back up before changes, and never print secret values.**

### Use Cases

- Check whether Claude Code / Claude Desktop residue still exists
- Clean Claude App, Claude PWA, Claude Code URL Handler, and Chrome Native Messaging bridge residue
- Inspect `ANTHROPIC_*`, `127.0.0.1:15721`, CC Switch / 302AI / GLM route leftovers
- Remove CC Switch app, cask, and `~/.cc-switch` state
- Monitor Claude network environment: IP purity, DNS leaks, WebRTC leaks, and node-region stability
- Run a post-ban three-step self-check: clear browser cookies/site data, remove CC Switch, and inspect Claude Code plus Claude Desktop
- Inspect browser fingerprint signals such as system timezone, `Intl` locale, browser language, and installed Chinese fonts
- Audit coding-agent config for route overrides, request rewriting, permission bypasses, and risky local gateway settings

### Install

Clone this repo into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/pnedfff/claude-env-cleanup.git ~/.codex/skills/claude-env-cleanup
```

Restart Codex, then invoke the `claude-env-cleanup` skill when needed.

### Read-Only Audit

Run the bundled audit script directly:

```bash
python3 ~/.codex/skills/claude-env-cleanup/scripts/audit_claude_env.py
```

The script reports safe summaries only, such as file presence, key-name presence, route markers, process/port status, and browser bridge state. It does not print raw tokens, API keys, OAuth refresh tokens, or private config values.

For network environment auditing, run:

```bash
python3 ~/.codex/skills/claude-env-cleanup/scripts/audit_network_env.py
```

By default it only checks local proxy, DNS, route, and browser-language state. Add `--external` when you want live public-IP and Claude reachability probes. Manual review defaults to 3 core sites only: `ip.net.coffee/claude`, `ippure.com/claude`, and `iplark.com`.

For post-ban self-checks:

```bash
python3 ~/.codex/skills/claude-env-cleanup/scripts/audit_network_env.py --post-ban
```

This mode prints browser site-data cleanup targets, clear manual-action reminders, and the 5 guide sites: `ip.net.coffee/claude`, `iplark.com`, `net.coffee`, `ippure.com`, and `cc.mastersgo.cc`.

### Safety Boundaries

- Do not delete anything by default.
- Browser cookies, Local Storage, IndexedDB, extensions, and full browser profiles are not deleted automatically; they are high-impact actions and must be handled manually or with explicit authorization.
- Create a timestamped backup before editing or removing files, usually under `/Users/<you>/Backups/`.
- Preserve Teamo, `~/.teamo`, and `~/.claude/projects` by default.
- Preserve `com.claude-to-im.bridge` by default; it may be a Codex/IM bridge rather than official Claude residue.
- Do not delete macOS system fonts. PingFang, Hiragino, STHeiti, and Songti/STSong may remain detectable by canvas font probes.
- Do not conflate general proxies such as ClashX with Claude-specific routing on `127.0.0.1:15721`.

### Repository Layout

```text
.
├── SKILL.md
├── agents/
│   └── openai.yaml
└── scripts/
    ├── audit_claude_env.py
    └── audit_network_env.py
```
