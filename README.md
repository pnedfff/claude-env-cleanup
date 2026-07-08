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
- 生成本机脱敏环境基线：时区、语言、出口地区、DNS、ASN、WebRTC 与 PWR 遥测指纹结论
- 开启官方 Claude Code 隐私控制：telemetry、error reporting、feedback、survey、nonessential traffic
- 梳理新账号早期使用和指纹重置 takeaways
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

审计脚本也会检查官方 Claude 隐私控制是否已在当前进程或 `~/.claude/settings*.json` 的 `env` 块中启用。

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

需要沉淀本机环境基线时，将脱敏后的档案放在：

```text
~/.claude/session-env/environment-fingerprint-profile.md
```

这份文件只应保存地区、时区、语言、代理本地端口、DNS 摘要、ASN/服务商、WebRTC 结论、PWR 遥测指纹风险结论等信息；不要保存完整公网 IP、局域网 IP、网关、Tailnet 地址、精确 WebRTC candidate、PWR 原始遥测 payload、Cookie、token 或密钥。

### 官方隐私控制

Claude Code 官方数据页说明可以用环境变量关闭遥测、错误上报、反馈命令、会话满意度调查和非必要流量。官方设置页说明这些环境变量也可以放进 `settings.json` 的顶层 `env` 对象。

推荐写入 `~/.claude/settings.json`：

```json
{
  "env": {
    "DISABLE_TELEMETRY": "1",
    "DISABLE_ERROR_REPORTING": "1",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "DISABLE_FEEDBACK_COMMAND": "1",
    "CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY": "1",
    "DO_NOT_TRACK": "1"
  }
}
```

注意：

- 这是隐私控制，不等于零数据保留，也不等于完整指纹重置。
- `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` 不会关闭 WebFetch 域名安全预检。
- `skipWebFetchPreflight: true` 是单独的 WebFetch 安全预检关闭项，有安全权衡，默认不建议自动设置。
- 修改后重启 Claude Code、Claude Desktop 和相关终端会话。

参考：

- [Claude Code data usage](https://code.claude.com/docs/en/data-usage)
- [Claude Code settings](https://code.claude.com/docs/en/settings)

Codex 可以自动做：

- 运行只读审计，读取时区、语言、代理、系统 DNS、默认路由、本地端口和公网出口摘要。
- 备份并合并官方隐私控制到 `~/.claude/settings.json` 的 `env` 块。
- 创建 `~/.claude/session-env/`。
- 写入脱敏候选档案。
- 复读检查文件里没有明显完整公网 IP、内网 IP、Tailnet 地址、WebRTC candidate、Cookie 或密钥。

用户需要手动做：

- 确认候选档案准确，确认后才标记为“用户确认过的本机环境基线”。
- 用真实浏览器打开 `ip.net.coffee/claude`、`ippure.com/claude`、`iplark.com`，确认 DNS/WebRTC/PWR/IP 风险。
- 改过时区、语言、代理、扩展或 Cookie 后，手动重启浏览器。
- 明确授权后才删除 Cookie、Local Storage、IndexedDB、扩展、浏览器 profile、Claude App、Claude Code 或 CC Switch。

### 新账号和指纹重置 takeaways

这些是经验性稳定使用建议，不保证消除账号风险：

- 新账号前两周优先使用官方 Claude Desktop/App 路径，避免独立 CLI。
- 新账号阶段不要使用 OpenCode、OpenClaw、CraftAgent 等第三方客户端。
- 账号要有作息，不要 24 小时持续高负载。
- IP 类型不是唯一重点；避免万人共用的公共代理，早期不要频繁切换 IP、地区或 ASN。
- 不共享账号。
- 被封后换账号前，指纹重置是重点：清理浏览器站点数据、扩展、Native Messaging、Claude App/Code 残留、CC Switch、本地 auth/config/cache/log/telemetry 残留，并重新做浏览器侧检测。
- 养号期可按约一个月或首次续费后理解，之后再逐步放松限制。

### 安全边界

- 默认不删除任何东西。
- 浏览器 Cookie、Local Storage、IndexedDB、扩展和整份浏览器 profile 不会自动删除；这些属于高影响动作，必须手动处理或明确授权后再做。
- 公开仓库只保存通用流程，不保存某台机器的完整 IP、内网、Tailnet 或 WebRTC candidate。
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
- Generate a sanitized local environment baseline: timezone, language, exit region, DNS, ASN, WebRTC, and PWR telemetry fingerprint verdicts
- Enable official Claude Code privacy controls for telemetry, error reporting, feedback, surveys, and nonessential traffic
- Summarize early-account usage and fingerprint-reset takeaways
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

The audit also checks whether official Claude privacy controls are enabled in the current process or in the `env` block of `~/.claude/settings*.json`.

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

For a reusable local environment baseline, store the sanitized profile at:

```text
~/.claude/session-env/environment-fingerprint-profile.md
```

The profile should keep region, timezone, languages, local proxy ports, DNS summary, ASN/provider, WebRTC verdicts, and PWR telemetry fingerprint risk verdicts only. Do not store full public IPs, LAN IPs, gateways, tailnet addresses, exact WebRTC candidates, raw PWR telemetry payloads, cookies, tokens, or secrets.

### Official Privacy Controls

Claude Code's official data usage page documents environment variables for disabling telemetry, error reporting, feedback, session surveys, and nonessential traffic. The official settings page says environment variables can also be configured under the top-level `env` key in `settings.json`.

Recommended `~/.claude/settings.json` values:

```json
{
  "env": {
    "DISABLE_TELEMETRY": "1",
    "DISABLE_ERROR_REPORTING": "1",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "DISABLE_FEEDBACK_COMMAND": "1",
    "CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY": "1",
    "DO_NOT_TRACK": "1"
  }
}
```

Notes:

- This is a privacy-control posture, not zero data retention or a full fingerprint reset.
- `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` does not disable the WebFetch domain safety check.
- `skipWebFetchPreflight: true` is a separate WebFetch safety-check opt-out with security tradeoffs and should not be set automatically by default.
- Restart Claude Code, Claude Desktop, and related terminal sessions after changing these values.

References:

- [Claude Code data usage](https://code.claude.com/docs/en/data-usage)
- [Claude Code settings](https://code.claude.com/docs/en/settings)

Codex can automatically:

- Run read-only audits for timezone, language, proxy, system DNS, default route, local ports, and public-exit summaries.
- Back up and merge official privacy controls into the `env` block of `~/.claude/settings.json`.
- Create `~/.claude/session-env/`.
- Write a sanitized candidate profile.
- Re-read the file to check that it does not contain obvious full public IPs, LAN IPs, tailnet addresses, WebRTC candidates, cookies, or secrets.

The user must manually:

- Confirm the candidate before it is treated as a user-confirmed local baseline.
- Open `ip.net.coffee/claude`, `ippure.com/claude`, and `iplark.com` in the real browser for DNS/WebRTC/PWR/IP-risk verdicts.
- Restart the browser after timezone, language, proxy, extension, or cookie changes.
- Explicitly approve deletion of cookies, Local Storage, IndexedDB, extensions, browser profiles, Claude App, Claude Code, or CC Switch.

### Early-Account and Fingerprint-Reset Takeaways

These are operational stability heuristics, not a guarantee that account risk is eliminated:

- For the first two weeks, prefer the official Claude Desktop/App path and avoid standalone CLI use.
- During the early account phase, avoid third-party clients such as OpenCode, OpenClaw, and CraftAgent.
- Keep a human-like work/rest rhythm; avoid continuous 24-hour high-load use.
- IP type is not the only signal; avoid crowded public proxies and avoid frequent IP, country, or ASN switching early on.
- Do not share accounts.
- After a ban, fingerprint reset is the key step before using a new account: clear browser site data, extensions, Native Messaging, Claude App/Code residue, CC Switch, local auth/config/cache/log/telemetry residue, then re-check in the real browser.
- Treat the warm-up period as roughly one month or after the first renewal, then relax constraints gradually.

### Safety Boundaries

- Do not delete anything by default.
- Browser cookies, Local Storage, IndexedDB, extensions, and full browser profiles are not deleted automatically; they are high-impact actions and must be handled manually or with explicit authorization.
- Public repos should contain only generic workflow instructions, not a specific machine's full IP, LAN, tailnet, or WebRTC candidate data.
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
