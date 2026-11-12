# Claude Env Cleanup Skill

> 中文说明在前，English follows.

## 中文

`claude-env-cleanup` 是一个 Codex skill，用于审计和清理 macOS 本机上的 Claude / CC Switch / coding-agent 环境残留。

它的默认原则是：**先只读审计，明确要求清理时才改动；改动前先备份；不打印密钥内容。**

**配套资源**

- 背景与手动步骤：[Claude 稳定使用配置清单](https://blog.1pro.men/posts/claude-stability-checklist/)（网络出口、DNS、WebRTC、Claude Code、新号节奏）
- 浏览器端自查：[1pro.men/whoami](https://1pro.men/whoami/)，在浏览器里看 IP、DNS、WebRTC、时区、语言和字体是否一致。本 skill 的脚本只看本机和命令行网络，浏览器能暴露的信号用这个页面补。

### 适用场景

- 检查 Claude Code / Claude Desktop 是否还有残留
- 清理 Claude App、Claude PWA、Claude Code URL Handler、Chrome Native Messaging bridge
- 排查 `ANTHROPIC_*`、`127.0.0.1:15721`、CC Switch / 302AI / GLM 路由残留
- 删除 CC Switch app、cask、`~/.cc-switch` 状态
- 监测 Claude 网络环境：IP 纯净度、DNS 泄露、WebRTC 泄露、节点地区稳定性
- Claude 账号被封后的三步自查：清浏览器 Cookie/站点数据、删除 CC Switch、检查 Claude Code 终端和桌面 App
- 生成本机脱敏环境基线：时区、语言、出口地区、DNS、ASN、WebRTC 与 PWR 指纹结论
- 开启官方 Claude Code 隐私控制：telemetry、error reporting、feedback、survey、nonessential traffic
- 梳理新账号早期使用和指纹重置 takeaways
- 检查 browser fingerprint 相关信号，例如系统时区、`Intl` locale、浏览器语言、中文字体探测
- 审计 coding-agent 配置中的路由覆盖、请求改写、权限绕过和高风险本地网关设置

### 安装

把这个仓库 clone 到 Codex skills 目录：

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/pnedfff/claude-env-cleanup.git ~/.agents/skills/claude-env-cleanup
```

重启 Codex 后即可通过 `claude-env-cleanup` skill 触发。

### 只读审计

可以直接运行内置审计脚本：

```bash
python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_claude_env.py --audit
```

脚本只输出安全摘要，例如配置文件是否存在、是否发现 key 名称、路由标记、进程/端口/浏览器桥接状态；不会打印 token、API key、OAuth refresh token 等原始值。

审计脚本也会检查官方 Claude 隐私控制是否已在当前进程或 `~/.claude/settings*.json` 的 `env` 块中启用。

网络环境审计可以运行：

```bash
python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_network_env.py
```

默认只做本机代理、DNS、路由、浏览器语言等只读检查。需要公网 IP / Claude 连通性时再加 `--external`。人工复核默认只使用 3 个核心网站：`ip.net.coffee/claude`、`ippure.com/claude`、`iplark.com`。

账号被封后的自查模式：

```bash
python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_network_env.py --post-ban
```

这个模式会列出浏览器站点数据的手动清理目标、醒目的手动动作提醒，以及文章里的 5 个复核网站：`ip.net.coffee/claude`、`iplark.com`、`net.coffee`、`ippure.com`、`cc.mastersgo.cc`。

需要沉淀本机环境基线时，将脱敏后的档案放在：

```text
~/.claude/session-env/environment-fingerprint-profile.md
```

这份文件只应保存地区、时区、语言、代理本地端口、DNS 摘要、ASN/服务商、WebRTC 结论、PWR 指纹风险结论等信息；不要保存完整公网 IP、局域网 IP、网关、Tailnet 地址、精确 WebRTC candidate、PWR 原始检测 payload、Cookie、token 或密钥。

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

**Companion resources**

- Background and manual steps: [Claude stability checklist](https://blog.1pro.men/posts/claude-stability-checklist/) (Chinese): exit node, DNS, WebRTC, Claude Code, new-account pacing.
- Browser-side self-check: [1pro.men/whoami](https://1pro.men/whoami/) shows whether IP, DNS, WebRTC, timezone, language and fonts agree in the browser. The scripts here only see the local machine and command-line network; use the page for browser-visible signals.

Its default posture is: **audit first, mutate only when explicitly asked, back up before changes, and never print secret values.**

### Use Cases

- Check whether Claude Code / Claude Desktop residue still exists
- Clean Claude App, Claude PWA, Claude Code URL Handler, and Chrome Native Messaging bridge residue
- Inspect `ANTHROPIC_*`, `127.0.0.1:15721`, CC Switch / 302AI / GLM route leftovers
- Remove CC Switch app, cask, and `~/.cc-switch` state
- Monitor Claude network environment: IP purity, DNS leaks, WebRTC leaks, and node-region stability
- Run a post-ban three-step self-check: clear browser cookies/site data, remove CC Switch, and inspect Claude Code plus Claude Desktop
- Generate a sanitized local environment baseline: timezone, language, exit region, DNS, ASN, WebRTC, and PWR fingerprint verdicts
- Enable official Claude Code privacy controls for telemetry, error reporting, feedback, surveys, and nonessential traffic
- Summarize early-account usage and fingerprint-reset takeaways
- Inspect browser fingerprint signals such as system timezone, `Intl` locale, browser language, and installed Chinese fonts
- Audit coding-agent config for route overrides, request rewriting, permission bypasses, and risky local gateway settings

### Install

Clone this repo into your Codex skills directory:

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/pnedfff/claude-env-cleanup.git ~/.agents/skills/claude-env-cleanup
```

Restart Codex, then invoke the `claude-env-cleanup` skill when needed.

### Read-Only Audit

Run the bundled audit script directly:

```bash
python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_claude_env.py --audit
```

The script reports safe summaries only, such as file presence, key-name presence, route markers, process/port status, and browser bridge state. It does not print raw tokens, API keys, OAuth refresh tokens, or private config values.

The audit also checks whether official Claude privacy controls are enabled in the current process or in the `env` block of `~/.claude/settings*.json`.

For network environment auditing, run:

```bash
python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_network_env.py
```

By default it only checks local proxy, DNS, route, and browser-language state. Add `--external` when you want live public-IP and Claude reachability probes. Manual review defaults to 3 core sites only: `ip.net.coffee/claude`, `ippure.com/claude`, and `iplark.com`.

For post-ban self-checks:

```bash
python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_network_env.py --post-ban
```

This mode prints browser site-data cleanup targets, clear manual-action reminders, and the 5 guide sites: `ip.net.coffee/claude`, `iplark.com`, `net.coffee`, `ippure.com`, and `cc.mastersgo.cc`.

For a reusable local environment baseline, store the sanitized profile at:

```text
~/.claude/session-env/environment-fingerprint-profile.md
```

The profile should keep region, timezone, languages, local proxy ports, DNS summary, ASN/provider, WebRTC verdicts, and PWR fingerprint risk verdicts only. Do not store full public IPs, LAN IPs, gateways, tailnet addresses, exact WebRTC candidates, raw PWR detection payloads, cookies, tokens, or secrets.

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


## 审计输出与检查完整性

脚本从自身目录加载 `scripts/audit_support.py`，安装时须保留完整 `scripts/` 目录。
本机实际入口为 `~/.agents/skills/claude-env-cleanup`；其他安装位置应使用实际技能目录，不依赖 `SKILL_DIR` 一定存在。

- `checked` 表示该检查已执行；`unknown` / `error` 表示采集不完整；`not_checked` 表示未请求或需人工检测。
- 退出码 `0` 表示请求范围内采集完成，不代表环境安全；`2` 表示采集不完整。未请求外部探测不会伪装成已检测。
- 历史比较仅对双方都有值的国家和 ASN 给出匹配或差异；无可比数据时无法判断稳定性。原始 IP 不保存，因此不会声称 IP 未变化。
- 新增历史记录仅保存脱敏后的国家、ASN、时区、匿名汇总语言和监听数量，不保存 IP、浏览器 profile 名称、任意服务响应或凭据。旧历史只读脱敏，不自动改写原件。
- 代理 URL 只显示协议、主机和端口；凭据、路径、查询、片段与无法解析的值不输出。错误只输出异常类型或固定错误类别。
- 原有备份、Teamo、共享会话、Claude-to-IM、通用代理和浏览器数据保护规则保持不变。

假数据回归（不运行真实环境审计）：

```bash
python3 ~/.agents/skills/claude-env-cleanup/scripts/test_audit_minimal.py
```


## 结构化清理审阅清单

默认运行 `audit_claude_env.py` 只生成固定 Claude 路径的元数据清单，不运行进程、包管理器或网络诊断，不读取配置、凭据或会话正文。原有详细只读诊断通过 `--audit` 显式开启，默认同样仅限 Claude；跨工具检查需显式 `--scope all`。

```bash
# 默认 Claude 清单，供人阅读
python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_claude_env.py

# 纯 JSON 清单，stdout 不混入日志
python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_claude_env.py --format json

# 显式跨工具配置元数据审阅；仍不清理
python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_claude_env.py --scope all --format json

# 原有详细只读 Claude 审计
python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_claude_env.py --audit
```

清单含稳定项目 ID、路径、类别、预期归属、检测状态、候选/审阅/保护判定、影响、保护原因和默认未选中状态。归属来自固定路径规则，不表示已核验安装身份；不存在的路径不称为候选。目录大小不递归计算。Teamo、Claude-to-IM 只记录保留政策而不访问其数据；共享会话、个人技能与旧备份始终受保护。文件或父目录符号链接不跟随，并标为检查不完整。

`executable: false`、`selected: false` 和 `review_only` 表示本轮仅供审阅。项目 ID 可用于生成临时测试工作区中的执行准备计划；清单本身不构成删除授权，也不是内容快照或恢复备份。真实清理入口仍关闭。`--audit` 与 `--format json` 不可组合，避免把纯元数据清单混同于详细诊断结果。

假目录生成的示例：`examples/cleanup-manifest.fixture.json`。它不代表本机实际状态。运行全部假数据回归：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s ~/.agents/skills/claude-env-cleanup/scripts -p 'test_*.py'
```


## 清理执行器：第三批，临时目录测试限定

`scripts/cleanup_executor.py` 提供 `FixtureWorkspace.prepare(manifest, ids)` 与 `execute(plan)`。工作区只能由内部 `TemporaryDirectory` 创建，不接受真实用户目录参数；直接运行该模块会拒绝真实清理。第三批测试使用假进程快照，第四批真实只读采集见下文；进程状态缺失或不完整时拒绝执行，绝不自动终止 Claude、Teamo 或 Claude-to-IM。

仅支持固定白名单中的缓存/日志候选项。配置、认证、应用/CLI 卸载、浏览器数据、跨工具项、共享会话、技能、Teamo、Claude-to-IM 与备份均不能借改写清单获得执行资格。现有保护规则不变。

执行步骤：

1. 按项目 ID 重建固定目标，不接受清单中的任意路径；拒绝重复/未知 ID、受保护项和需人工审阅项。旧 schema 1 清单必须重新生成。
2. schema 2 清单记录文件身份元数据；准备阶段复核元数据并生成目录/文件的身份与 SHA-256 内容快照。返回含 ID、路径、影响动作、条目数和字节数的一次性审阅计划，尚不备份或清理。
3. 执行阶段核对注册计划、父目录身份、内容快照及完整进程状态。拒绝符号链接、硬链接、特殊文件、外部所有权、不安全路径和超限扫描；使用排他事务锁。
4. 在私有备份目录保存所有选中项，以内容摘要、文件大小与完整目录结构验证备份，并写入及读回备份清单。全部通过才允许第一项删除；每项执行前再核对本项备份、源对象和进程。
5. 原对象按目录描述符原子移动到隔离暂存区，再核对实际移入的对象和进程后删除。原路径上新出现的文件不会被删除或覆盖。
6. 任一错误立即停止，回执分别记录已删除、未执行、执行前失败、暂存保留或删除失败可能部分完成。已删除项不自动回滚；备份和残余暂存数据用于显式恢复。错误只输出固定原因或异常类型。

这是临时目录测试实现，不是已验收的生产清理器；测试上下文退出后临时备份也会删除，不能当成真实用户数据的恢复方案。`examples/cleanup-execution.fixture.json` 仅为假数据成功/失败回执示例。真实路径的写入执行与恢复操作仍未开放；第四批增加真实只读采集和路径预检。

只运行假数据回归：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s ~/.agents/skills/claude-env-cleanup/scripts -p 'test_*.py'
```


## 第四批：真实进程采集与生产路径只读预检

`scripts/production_preflight.py` 只读检查当前用户可见进程和固定 Claude 候选路径，输出清理计划与备份方案；没有创建备份、修改配置、停止进程或删除数据的代码入口。

```bash
python3 ~/.agents/skills/claude-env-cleanup/scripts/production_preflight.py --format markdown
python3 ~/.agents/skills/claude-env-cleanup/scripts/production_preflight.py --format json
```

- `ps` 仅读取 PID、父 PID、UID 和 executable/comm，不读取命令参数；`lsof` 检查所采集 PID 的文件引用，`launchctl print` 检查 Claude-to-IM 服务。原始输出不显示或写入报告，报告只保留 PID、固定分组和检测状态。
- 名称与文件引用不是官方安装归属证明。Teamo、Claude-to-IM 和共享 Claude 状态的使用者只会成为执行阻塞证据，不会被列为卸载对象或被自动终止。两次进程采样变化、权限不足、工具缺失或解析不完整均标为未知。
- 默认只预检固定 Claude 缓存/日志候选项，以目录描述符检查符号链接、硬链接、对象类型、所有权和元数据变化。不读取文件正文；10,000 个条目或 10 秒达到上限时标为未知，不声称完整大小或内容验收。
- 清理计划始终 `executable: false` 且所有项未选中；保护名单与影响会列入计划。生产报告不能交给临时执行器。
- 备份仅提出 `~/Backups/ClaudeCleanup/<plan-id>` 的方案，检查现有父路径、容量下限与访问条件，不做写入试验。目录权限拟为 0700，文件拟为 0600；任何清理前须对全部选中项做内容摘要、目录结构、源状态和备份清单读回验证。
- 若任何目录大小未知，备份总容量与所需空间估算保持未知，仅报告已扫描部分和最低空间下限。容量预检不能替代实际备份成功验证。
- 自定义 `CLAUDE_CONFIG_DIR` 仅报告需另行明确范围，不自动扩大扫描，不显示其私有值。
- 退出码 2 表示有阻塞；0 仅表示已测范围内没有已知阻塞，仍需审阅、准确项目授权及重新采样。真实路径写入执行入口继续关闭。

本机预检报告属于本地用户资料，应写入工作区 `outputs/` 或指定本地目录，不提交到公开技能仓库。脚本 stdout 默认仅输出报告，不默认落盘。
