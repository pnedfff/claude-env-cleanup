---
name: claude-env-cleanup
description: Audit, clean, and when explicitly requested uninstall local Claude Code, Claude Desktop/PWA, Anthropic browser Native Messaging, Claude Chrome extensions, auth/config residue, CC Switch app/data/routes, Claude network signals, DNS/WebRTC leaks, browser locale/timezone/font signals, and coding-agent config risks on Kevin's Mac while preserving Teamo Code and Claude-to-IM by default. Use for "Claude 环境清理", "清理 Claude 残留", "本地 coding agent 配置清理", "请求链路体检", "网络环境监测", "Claude 网络检测", "DNS 泄露", "WebRTC 泄露", "IP 纯净度", "节点地区稳定", "清理代理/中转/遥测/权限绕过", "卸载 Claude", "删除官方 Claude App", "删除 Claude PWA", "删除 Claude Code URL Handler", "删除 Claude Chrome 扩展", "清理 com.anthropic.claude_browser_extension", "CC Switch 可以删掉", "删除 CC Switch", "ANTHROPIC_*", "127.0.0.1:15721", "系统时区", "Asia/Singapore", "浏览器语言", "Intl 区域设置", "已安装中文字体", "canvas 字体探测", or when a Claude artifact may really be a CLI, app, LaunchAgent, proxy, browser bridge, or config needing backup-first inspection and cleanup.
---

# Claude Env Cleanup

## Safety Contract

Default to audit-only until the user explicitly asks to clean. Never print raw secrets, tokens, API keys, OAuth values, refresh tokens, or full private config values. Report only key presence, route markers, table/column hits, process names, and safe operational implications.

Before destructive or mutating work, create a timestamped backup under `/Users/kevin/Backups/` or next to the file being edited, then state the backup path. Make minimal scoped edits. Do not remove unrelated proxies, especially ClashX on `7890`, when the problem is Claude-specific routing on `127.0.0.1:15721`.

Uninstall official Claude App or Claude Code itself only when the user explicitly asks to delete, remove, or uninstall the body/app/CLI. When that explicit request exists, stop running confirmed official Claude processes first, move app/data/browser-bridge residue to Trash or a timestamped backup folder, uninstall package-manager installs with the package manager when possible, and verify that the binary/app no longer exists. Treat Chrome PWA shortcuts, `Claude Code URL Handler.app`, Anthropic Native Messaging manifests, and Claude browser extensions as app/CLI entry points when the user asks to remove Claude App and Claude Code.

Preserve Teamo Code unless the user separately and explicitly asks to remove Teamo. Preserve `com.claude-to-im.bridge` and `/Users/kevin/code/Claude-to-IM-skill` unless the user explicitly asks to remove that bridge; Kevin uses it as a Codex integration, not as proof of official Claude. Do not delete `/opt/homebrew/bin/teamo`, `@teamolab/teamo-cli`, `~/.teamo`, or `~/.claude/projects`. Teamo terminal verification can depend on `~/.teamo/*` and session JSONL files under `~/.claude/projects`. If a short-lived `claude` process appears with parent `teamo`, treat it as Teamo runtime behavior, not proof that the official Claude Code binary is still installed.

For coding-agent config hygiene, distinguish active config from historical evidence. Audit active config files first. Do not recursively grep session logs, debug logs, caches, plugin bundles, or backups by default; they create noise and can expose private content. Move historical debug/telemetry/router backups only when the user asks to clean local residue or privacy traces.

For browser locale, timezone, and font signal work, report consistency facts and safe local changes only. Do not delete macOS system fonts or system-protected font assets. It is acceptable to move user-installed fonts to a timestamped backup and clear the user font cache when explicitly requested, but state that macOS system fonts such as PingFang, Hiragino, STHeiti, and Songti/STSong may still be detectable.

For Claude network environment monitoring, prefer browser-visible facts for DNS/WebRTC/IP quality. Local command output is useful for proxy, route, resolver, and history checks, but DNS leak verdicts should be based on browser-side detection whenever possible. Do not open a large battery of sites by default; use only the three core manual checks listed below unless the user asks for more.

## Quick Audit

Run the bundled read-only audit first:

```bash
python3 "$SKILL_DIR/scripts/audit_claude_env.py"
```

If `SKILL_DIR` is not set, resolve it from the skill folder path and run:

```bash
python3 ~/.codex/skills/claude-env-cleanup/scripts/audit_claude_env.py
```

Use the output to decide which workflow applies. If the audit finds sensitive keys, say only that the key exists and where it is configured, not its value.

For network environment monitoring, run the read-only network audit:

```bash
python3 ~/.codex/skills/claude-env-cleanup/scripts/audit_network_env.py
```

When the user explicitly wants live public-IP and Claude reachability checks, add `--external`. To track whether the node region changes over time, append a history snapshot:

```bash
python3 ~/.codex/skills/claude-env-cleanup/scripts/audit_network_env.py --external --append-history ~/.codex/network-env-history.jsonl
```

## Decision Flow

1. If the user only asks whether Claude leftovers exist, run audit-only and summarize:
   - Claude config files present or missing
   - `ANTHROPIC_*` key presence
   - route markers such as `127.0.0.1:15721`, `PROXY_MANAGED`, `api.302.ai`, `302ai-claude-code`, `glm-5.2`
   - CC Switch DB/table hits
   - whether port `15721` is listening

2. If the user wants Claude Code back on official `claude.ai` auth, preserve active non-official routes unless they explicitly ask to abandon them. Focus on stale official-profile values in `~/.cc-switch/cc-switch.db` and high-priority env values in `~/.claude/settings.json` that can trigger "connectors disabled because ANTHROPIC_API_KEY or another auth source takes precedence".

3. If the user wants to remove non-official Claude routing, back up and then remove Claude-specific route overrides from:
   - `~/.claude/settings.json`
   - `~/.codex/config.toml`
   - `~/.cc-switch/settings.json`
   - `~/.cc-switch/cc-switch.db`

4. If the user says CC Switch can be deleted or asks to remove it completely, use the "Remove CC Switch App and State" pattern below. This is broader than route cleanup: include the Homebrew cask, `/Applications/CC Switch.app`, `~/.cc-switch`, process state, LaunchAgents, and port `15721`, while preserving unrelated Codex/Teamo/Claude-to-IM bridge components.

5. If the user asks about browser/system detection signals such as time zone, browser language, `Intl` locale, timezone offset, emoji style, or installed Chinese fonts, use the "Locale, Time Zone, and Font Signal Hygiene" pattern. Restart browser-family apps before trusting post-change results because browser runtimes can cache timezone and font state.

6. If the user asks about Claude network environment, IP purity, DNS leak, WebRTC leak, or node stability, use the "Claude Network Environment Monitoring" pattern. Prefer current browser results from the three core sites over command-line-only conclusions.

7. If the user calls something a Claude "skill" but it may be an installed artifact, verify the artifact class first:
   - skill folder
   - global npm or Homebrew CLI
   - app bundle
   - LaunchAgent
   - local data directory
   - log directory

Then clean the actual artifact class, not the label the user guessed.

8. If the user explicitly asks to delete official Claude App or Claude Code itself, use the "Uninstall Official Claude App and Claude Code" pattern below. This is a broader uninstall than route cleanup; include app bundles, package-manager installs, binaries, LaunchAgents, updater jobs, app support data, caches, preferences, saved state, and logs where present.

9. If Teamo or `com.claude-to-im.bridge` is mentioned, run a preservation check before and after cleanup: verify `teamo` still resolves, `~/.teamo` still exists, `~/.claude/projects` is not removed, and the bridge is still present/running when it was intentionally preserved.

10. If the user asks to clean local coding-agent configs based on request-chain trust rules, audit for four categories:
   - provider route overrides: `ANTHROPIC_BASE_URL`, `OPENAI_BASE_URL`, `api_base_url`, `baseUrl`, local proxy ports, third-party routers
   - request rewriting surfaces: Claude Code Router, provider transformers, gateway adapters, custom system-prompt/status-line commands
   - permission bypasses: `bypassPermissions`, skipped dangerous-mode prompts, unsafe host-header fallback
   - telemetry/debug residue: failed event files, debug logs, obsolete router logs, old DB/env backups containing key names

Clean only active-risk items by default. Preserve intentional tools and credentials unless the user asks to remove the tool itself.

## Known Local Surfaces

Treat these as the high-yield inspection points:

- `~/.claude/settings.json`
- `~/.claude/settings.bailian.json` (separate profile; do not merge with main route)
- `~/.claude.json`
- `~/.codex/config.toml`
- `~/.cc-switch/settings.json`
- `~/.cc-switch/cc-switch.db`
- `/Applications/CC Switch.app`
- Homebrew cask `cc-switch`
- `~/.claude-code-router/config.json`
- `~/.cursor/mcp.json`
- `~/.gemini/settings.json`
- `~/.gemini/config/mcp_config.json`
- `~/.kiro/settings/cli.json`
- `~/.openclaw-lan-u*/openclaw.json`
- `~/.claude-sync/config.json`
- `~/Library/LaunchAgents/`
- `~/Library/Logs/`
- `/Applications/Claude.app`
- `~/Applications/Chrome Apps.localized/Claude.app` (Chrome PWA shortcut to `https://claude.ai/`)
- `~/Applications/Claude Code URL Handler.app` (official Claude Code deep-link handler for `claude-cli://`)
- Chromium Native Messaging manifests:
  - `~/Library/Application Support/*/NativeMessagingHosts/com.anthropic.claude_browser_extension.json`
  - `~/Library/Application Support/*/*/NativeMessagingHosts/com.anthropic.claude_browser_extension.json`
  - `~/Library/Application Support/*/NativeMessagingHosts/com.anthropic.claude_code_browser_extension.json`
  - `~/Library/Application Support/*/*/NativeMessagingHosts/com.anthropic.claude_code_browser_extension.json`
- Claude Chrome extension IDs observed in manifests or installed profiles:
  - `fcoeoabgfenejglbffodgkkbkcdhcgfn` (`Claude in Chrome (Beta)` observed locally)
  - `dihbgbndebgnbjfmelmegjepbnkhlgni`
  - `dngcpimnedloihjnnfngkgjoidhnaolf`
- global npm package `@anthropic-ai/claude-code`
- official npx cache paths such as `~/.npm/_npx/*/node_modules/@anthropic-ai/claude-code`
- Teamo Code preservation surfaces: `/opt/homebrew/bin/teamo`, global package `@teamolab/teamo-cli`, `~/.teamo`, and `~/.claude/projects`
- Claude Code binaries found by `which -a claude` or likely bin folders such as `~/.npm-global/bin`, `~/.local/bin`, `/opt/homebrew/bin`, and `/usr/local/bin`
- Claude app data under `~/Library/Application Support/Claude*`
- Claude app caches, preferences, saved state, and logs under `~/Library/`
- Claude Code local cache and state markers such as `~/Library/Caches/claude-cli-nodejs` and `~/.claude-code-now-last-dir`
- Shared Claude/Teamo state markers such as `~/.claude` and `~/.claude.json`; these may reappear and are not proof by themselves that official Claude Code is still installed
- current process environment for `ANTHROPIC_*`
- listener on `127.0.0.1:15721`
- locale/timezone and browser-signal checks: `/etc/localtime`, `systemsetup -gettimezone` when sudo is available, `date`, browser language/locale settings, `~/Library/Fonts`, `/Library/Fonts`, and macOS system font locations
- network environment checks: `scutil --proxy`, `scutil --dns`, `route -n get default`, watched proxy ports such as `7890`, `7892`, `1080`, `8080`, `8888`, and browser-visible public IP/DNS/WebRTC checks

Route residue indicators include `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`, `ANTHROPIC_MODEL_NAME`, `OPENAI_BASE_URL`, `PROXY_MANAGED`, `127.0.0.1:15721`, `302ai-claude-code`, `claude-official`, `api.302.ai`, `glm-5.2`, `proxy_live_backup`, `claude-code-router`, `openrouter`, `anyrouter`, `api.deepseek.com`, `open.bigmodel.cn`, `teamocode.com`, and `code.newcli.com`.

Permission-risk indicators include `bypassPermissions`, `skipDangerousModePermissionPrompt`, and `dangerouslyAllowHostHeaderOriginFallback`.

## Cleanup Patterns

### Disable Non-Official Claude Proxy Routing

Use when the user wants Claude Code to stop using CC Switch or a local Anthropic-compatible proxy.

1. Back up `~/.claude/settings.json`, `~/.codex/config.toml`, `~/.cc-switch/settings.json`, and `~/.cc-switch/cc-switch.db`.
2. Remove Claude-specific `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, and related default-model route overrides from Claude/Codex config.
3. In `~/.cc-switch/settings.json`, set `launchOnStartup: false`, `enableLocalProxy: false`, and `currentProviderClaude: claude-official` when those fields exist.
4. In `~/.cc-switch/cc-switch.db`, remove only non-official Claude providers or Claude proxy env values requested by the user.
5. Stop `CC Switch.app` or the relevant helper process.
6. Verify `127.0.0.1:15721` is no longer listening, unless the user intentionally keeps CC Switch running.

### Clean Stale Official-Profile Auth

Use when Claude Code has a valid `claude.ai` OAuth account but connectors are disabled due to a higher-priority API key or proxy auth source.

1. Back up `~/.cc-switch/cc-switch.db`.
2. Locate the `claude-official` provider/config row.
3. Remove `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_API_KEY`, and `ANTHROPIC_BASE_URL` from that official profile only.
4. Preserve active proxy profiles such as `302ai-claude-code` unless the user asks to remove them.
5. Restart or refresh the relevant Claude/CC Switch process.

### Remove CC Switch App and State

Use when the user explicitly says CC Switch can be deleted or asks to remove CC Switch itself.

1. Inventory first without printing secrets:
   - `/Applications/CC Switch.app`
   - `~/.cc-switch`
   - Homebrew cask `cc-switch`
   - `which -a cc-switch ccswitch`
   - `ps ax -o pid=,ppid=,comm=` matches for `CC Switch|cc-switch|ccswitch`
   - `launchctl list` and `~/Library/LaunchAgents` matches for CC Switch
   - `lsof -nP -iTCP:15721 -sTCP:LISTEN`
2. Create `/Users/kevin/Backups/cc-switch-delete-<timestamp>/` with `inventory/`, `files/`, and `removed/`.
3. Copy `/Applications/CC Switch.app` and `~/.cc-switch` into `files/` before deletion or movement.
4. Uninstall the cask with `HOMEBREW_NO_AUTO_UPDATE=1 brew uninstall --cask cc-switch`, capturing stdout/stderr into `inventory/`.
5. Move any remaining `~/.cc-switch` and `/Applications/CC Switch.app` into `removed/`.
6. Verify:
   - `/Applications/CC Switch.app` is absent
   - `~/.cc-switch` is absent
   - `brew list --cask` no longer shows `cc-switch`
   - `which -a cc-switch ccswitch` finds nothing
   - no CC Switch process or LaunchAgent is running
   - `127.0.0.1:15721` is not listening
7. Preserve `com.claude-to-im.bridge`, Codex, Teamo, and `~/.claude/projects` unless the user separately asks to remove them.

### Installed Artifact Cleanup

Use when a name might be a skill, CLI, service, or app.

1. Search skill roots first.
2. If no skill matches, check `which -a`, package-manager listings, `launchctl list`, `~/Library/LaunchAgents`, and likely data/log folders.
3. Back up or move residual state to Trash rather than permanently deleting it unless the user explicitly asks for deletion.
4. Verify the binary, LaunchAgent, process, and residual folders are gone or intentionally preserved.

### Coding-Agent Request Chain Hygiene

Use when the user asks to apply the high-permission coding-agent trust rule.

1. Inventory active config only:
   - Claude: `~/.claude/settings.json`, `~/.claude/settings.local.json`, `~/.claude.json`
   - Codex: `~/.codex/config.toml`, `~/.codex/auth.json` presence only
   - Teamo: `~/.teamo/settings.json`, `~/.teamo/auth.json` presence only
   - CC Switch: `~/.cc-switch/settings.json`, `~/.cc-switch/cc-switch.db`
   - Claude Code Router: `~/.claude-code-router/config.json`
   - Cursor/Gemini/Kiro/OpenClaw: their MCP/settings JSON files
   - LaunchAgents and Native Messaging hosts
2. Classify each finding:
   - intentional active route
   - stale route residue
   - permission bypass
   - request rewrite/transformer
   - telemetry/debug/history residue
3. Back up before mutation.
4. Remove or archive stale third-party router configs such as inactive `~/.claude-code-router`.
5. Remove permission-bypass defaults from active config unless the user explicitly wants always-on dangerous mode.
6. Set OpenClaw local gateway `dangerouslyAllowHostHeaderOriginFallback` to false unless the user explicitly needs LAN host-header fallback.
7. Move debug/telemetry/router logs and old key-bearing backups out of active home folders when the user asks for privacy cleanup; keep them in a timestamped backup instead of deleting permanently.
8. Preserve Teamo, Codex auth, project sessions, and bridge runtimes unless removal is explicitly requested.

### Locale, Time Zone, and Font Signal Hygiene

Use when the user is comparing local browser/system signals such as `Intl.DateTimeFormat().resolvedOptions().timeZone`, `navigator.languages`, `Intl` locale, `getTimezoneOffset()`, emoji style, or canvas font detection.

1. Time zone:
   - Set Singapore with `sudo systemsetup -settimezone "Asia/Singapore"` when explicitly requested.
   - If macOS prints `Error:-99` but also says `Set TimeZone: Asia/Singapore`, verify with `readlink /etc/localtime`; the change may have succeeded.
   - Use `sudo systemsetup -gettimezone` or `readlink /etc/localtime` for verification.
   - Remember `Asia/Shanghai` and `Asia/Singapore` are both `UTC+8`, so `getTimezoneOffset()` remains unchanged even when the IANA timezone changes.
   - Restart browser/Codex/Claude after changing timezone because runtimes can cache timezone at startup.
2. Fonts:
   - First inspect `~/Library/Fonts` and `/Library/Fonts`.
   - Move only user-installed fonts to a timestamped backup such as `~/Desktop/font-backup-<timestamp>/` when the user explicitly asks to test removal.
   - Clear user font cache with `atsutil databases -removeUser` and restart `fontd` with `killall fontd`.
   - Do not delete macOS system fonts or protected assets. PingFang, Hiragino Sans GB, STHeiti, and Songti/STSong are expected macOS signals and can remain detectable even after user fonts are removed.
3. Browser language and `Intl` locale are separate from system timezone and fonts. Treat them as browser/profile settings, not font cleanup.
4. Be honest about limits: normal Chrome on macOS cannot fully hide system font availability; a clean browser profile, anti-fingerprinting browser, VM, or remote environment may be needed for a different fingerprint.

### Claude Network Environment Monitoring

Use when the user asks to check Claude network environment, IP purity, DNS leak, WebRTC leak, node region stability, or the "5 checks" from a Claude usage guide.

1. Run the local audit first:
   - `python3 ~/.codex/skills/claude-env-cleanup/scripts/audit_network_env.py`
   - Add `--external` only when live public-IP and Claude endpoint requests are appropriate.
   - Add `--append-history ~/.codex/network-env-history.jsonl` when the user wants node-region drift monitoring.
2. Open only these three core browser checks by default:
   - `https://ip.net.coffee/claude/` for Claude-specific IP trust, Claude reachability, DNS/WebRTC links, timezone, and language.
   - `https://ippure.com/claude` for Claude environment, DNS/WebRTC status, and Chinese-fingerprint score.
   - `https://iplark.com/` for independent IP intelligence, geo consistency, ASN/provider, and IP score.
3. Treat DNS leak as a browser-side verdict:
   - Good: public exit IP is overseas and DNS resolver exits are overseas, hidden by DoH/DoT, or reported as normal/no leak.
   - Bad: public exit IP is overseas but DNS resolver IPs show China/local ISP or a different unexpected region.
   - `scutil --dns` is only supporting evidence; Chrome may resolve through the proxy differently from the terminal.
4. Treat these as watch items rather than automatic cleanup targets:
   - IPv6 Claude exit when a page warns that IPv6 is not recommended for Claude Code.
   - data-center or hosting IP instead of residential IP.
   - mixed IPv4/IPv6 or mixed-country outbound results.
   - browser language/Intl/font signals that still look Chinese.
5. Report a compact verdict:
   - IP/ASN/region
   - risk score or trust score from each site
   - DNS leak status
   - WebRTC leak status
   - Claude reachability
   - residual browser/system fingerprint risks

### Uninstall Official Claude App and Claude Code

Use only after the user explicitly asks to remove the official app or CLI itself.

1. Inventory before uninstall:
   - `which -a claude`
   - package-manager records for `@anthropic-ai/claude-code`
   - official npx cache records for `@anthropic-ai/claude-code`
   - `/Applications/Claude.app`
   - `~/Applications/Chrome Apps.localized/Claude.app`
   - `~/Applications/Claude Code URL Handler.app`
   - Anthropic Native Messaging manifests under Chromium browser profile roots
   - Claude browser extensions in Chrome profiles, especially IDs `fcoeoabgfenejglbffodgkkbkcdhcgfn`, `dihbgbndebgnbjfmelmegjepbnkhlgni`, and `dngcpimnedloihjnnfngkgjoidhnaolf`
   - running processes matching `Claude`, `claude`, or `Anthropic`
   - launchd entries matching `claude` or `anthropic`
   - app support/cache/preference/log paths under `~/Library/`
2. Create a timestamped backup or Trash staging directory. Store both a pre-uninstall inventory and config snapshots such as `~/.claude/settings.json`, `~/.claude/settings.local.json`, `~/.claude.json`, `~/.cc-switch/settings.json`, and `~/.cc-switch/cc-switch.db` when present.
3. Stop running confirmed Claude Desktop and Claude Code processes. Leave unrelated bridges, Codex processes, `com.claude-to-im.bridge`, and Teamo processes alone unless the user asks to remove them. If a `claude` process has parent `teamo`, verify with `ps`/`lsof` before killing and preserve Teamo by default.
4. Uninstall Claude Code with npm if it is installed as `@anthropic-ai/claude-code`; then remove leftover `claude` symlinks or version folders only after confirming they belong to Claude Code.
5. Move `/Applications/Claude.app`, `~/Applications/Chrome Apps.localized/Claude.app`, and `~/Applications/Claude Code URL Handler.app` to Trash or the staging directory when present.
6. Move official Claude Desktop residue to Trash/staging:
   - `~/Library/Application Support/Claude`
   - `~/Library/Application Support/com.anthropic.claudefordesktop`
   - `~/Library/Caches/com.anthropic.claudefordesktop`
   - `~/Library/Caches/com.anthropic.claudefordesktop.ShipIt`
   - `~/Library/Caches/claude-cli-nodejs`
   - `~/Library/HTTPStorages/com.anthropic.claudefordesktop`
   - `~/Library/Preferences/com.anthropic.claudefordesktop.plist`
   - `~/Library/Preferences/ByHost/com.anthropic.claudefordesktop*.plist`
   - `~/Library/Saved Application State/com.anthropic.claudefordesktop.savedState`
   - `~/Library/Logs/Claude`
7. Move official Claude Code state markers such as `~/.claude.json` and `~/.claude-code-now-last-dir` only when the user asks to delete the Claude Code terminal program or local records. Keep a copy in the timestamped backup. If `~/.claude.json` reappears with only migration/user metadata and there is no `claude` binary/app/package, report it as a shared runtime state marker rather than proof of official Claude Code still being installed.
8. Move Anthropic Native Messaging manifests to Trash/staging. These are browser-side bridge pre-authorisations; deleting Claude.app alone can leave a broken manifest such as `com.anthropic.claude_browser_extension.json` in Chrome.
9. If a Claude browser extension is installed, report it separately and either:
   - ask the user to remove it through `chrome://extensions` when only auditing, or
   - move the matching extension ID folder to backup/staging when the user explicitly asked to delete Claude browser integration residue. Do not delete unrelated Chrome profile data.
10. Preserve shared local state by default. Do not remove `~/.claude/projects`, `~/.claude/skills`, `~/.teamo`, or `~/.claude-to-im` during official Claude uninstall. If cleaning official Claude Code data is explicitly requested, move only confirmed official-auth/cache items and keep project/session data available for Teamo.
11. Verify `claude` is no longer on PATH, `/Applications/Claude.app` and user-level Claude app shortcuts are absent, global/npx `@anthropic-ai/claude-code` entries are absent, Anthropic Native Messaging manifests are absent, Claude browser extension IDs are absent or intentionally preserved, Claude processes are stopped, and launchd no longer reports active official Claude updater jobs.
12. Verify Teamo if it was in scope: `teamo --version` still works, `~/.teamo` exists, and the expected `~/.claude/projects` session files remain.

## Verification

After edits, verify with targeted checks:

- JSON files parse with `python3 -m json.tool`
- SQLite DB opens with `sqlite3`
- route markers are absent or intentionally present
- `lsof -nP -iTCP:15721 -sTCP:LISTEN` matches the intended state
- Claude/Codex config no longer contains unexpected `ANTHROPIC_*` route overrides
- CC Switch app/cask/data are absent when removal was requested
- coding-agent active configs no longer contain stale router endpoints, permission-bypass defaults, or unsafe Host Header fallback unless intentionally preserved
- `/etc/localtime` points to the intended timezone after timezone changes
- `~/Library/Fonts` user-installed fonts are absent or intentionally present after font-signal tests
- network audit reports expected proxy/DNS/default-route state, browser checks show no DNS/WebRTC leak, and history does not show unintended country/ASN drift when monitoring is enabled
- for app/CLI/browser-bridge uninstall, `/Applications/Claude.app`, `~/Applications/Chrome Apps.localized/Claude.app`, and `~/Applications/Claude Code URL Handler.app` are absent, `which -a claude` finds nothing, `npm list -g --depth=0` and `~/.npm/_npx` have no `@anthropic-ai/claude-code`, `~/Library/Caches/claude-cli-nodejs` is absent, Anthropic Native Messaging manifests are absent, Claude browser extension IDs are absent or intentionally preserved, and no official Claude process remains
- for Teamo and bridge preservation, `which -a teamo` or `/opt/homebrew/bin/teamo --version` still works, `~/.teamo` plus `~/.claude/projects` remain, and intentionally preserved `com.claude-to-im.bridge` remains loaded/running

When reporting results, separate:

- current facts verified in this run
- changes made
- backup paths
- residual risks or intentionally preserved routes
