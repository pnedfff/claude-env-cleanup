---
name: claude-env-cleanup
description: Audit, clean, and when explicitly requested uninstall local Claude Code, Claude Desktop/PWA, Anthropic browser bridges/extensions, auth/config residue, CC Switch app/data/routes, Claude network signals, DNS/WebRTC leaks, browser locale/timezone/font signals, PWR fingerprint signals, environment fingerprint baseline, official Claude privacy controls, and coding-agent config risks on Kevin's Mac while preserving Teamo Code and Claude-to-IM by default. Use for "Claude 环境清理", "清理 Claude 残留", "Claude 封号", "被封账号后", "封号自查", "指纹重置", "养号期", "清除浏览器 Cookie", "Claude 隐私控制", "DISABLE_TELEMETRY", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "网络环境监测", "环境指纹档案", "PWR 指纹", "DNS 泄露", "WebRTC 泄露", "IP 纯净度", "卸载 Claude", "删除官方 Claude App", "删除 Claude Code", "CC Switch 可以删掉", "删除 CC Switch", "ANTHROPIC_*", "127.0.0.1:15721", "系统时区", "Asia/Singapore", "浏览器语言", "canvas 字体探测", or when a Claude artifact may be a CLI, app, LaunchAgent, proxy, browser bridge, or config needing backup-first inspection and cleanup.
---

# Claude Env Cleanup（Claude 环境清理）

# Claude Env Cleanup

## Safety Contract

Default to audit-only until the user explicitly asks to clean. Never print raw secrets, tokens, API keys, OAuth values, refresh tokens, or full private config values. Report only key presence, route markers, table/column hits, process names, and safe operational implications.

Before destructive or mutating work, create a timestamped backup under `~/Backups/` or next to the file being edited, then state the backup path. Make minimal scoped edits. Do not remove unrelated proxies, especially ClashX on `7890`, when the problem is Claude-specific routing on `127.0.0.1:15721`.

Uninstall official Claude App or Claude Code itself only when the user explicitly asks to delete, remove, or uninstall the body/app/CLI. When that explicit request exists, stop running confirmed official Claude processes first, move app/data/browser-bridge residue to Trash or a timestamped backup folder, uninstall package-manager installs with the package manager when possible, and verify that the binary/app no longer exists. Treat Chrome PWA shortcuts, `Claude Code URL Handler.app`, Anthropic Native Messaging manifests, and Claude browser extensions as app/CLI entry points when the user asks to remove Claude App and Claude Code.

Preserve Teamo Code unless the user separately and explicitly asks to remove Teamo. Preserve `com.claude-to-im.bridge` and `~/code/Claude-to-IM-skill` unless the user explicitly asks to remove that bridge; Kevin uses it as a Codex integration, not as proof of official Claude. Do not delete `/opt/homebrew/bin/teamo`, `@teamolab/teamo-cli`, `~/.teamo`, or `~/.claude/projects`. Teamo terminal verification can depend on `~/.teamo/*` and session JSONL files under `~/.claude/projects`. If a short-lived `claude` process appears with parent `teamo`, treat it as Teamo runtime behavior, not proof that the official Claude Code binary is still installed.

For coding-agent config hygiene, distinguish active config from historical evidence. Audit active config files first. Do not recursively grep session logs, debug logs, caches, plugin bundles, or backups by default; they create noise and can expose private content. Move historical debug/telemetry/router backups only when the user asks to clean local residue or privacy traces.

For browser locale, timezone, and font signal work, report consistency facts and safe local changes only. Do not delete macOS system fonts or system-protected font assets. It is acceptable to move user-installed fonts to a timestamped backup and clear the user font cache when explicitly requested, but state that macOS system fonts such as PingFang, Hiragino, STHeiti, and Songti/STSong may still be detectable.

For Claude network environment monitoring, prefer browser-visible facts for DNS/WebRTC/IP quality. Local command output is useful for proxy, route, resolver, and history checks, but DNS leak verdicts should be based on browser-side detection whenever possible. Do not open a large battery of sites by default; use only the three core manual checks listed below unless the user asks for more.

Browser cookie and site-data cleanup is a manual, high-blast-radius step. In post-ban workflows, report the relevant browser profile targets and give clear manual steps. Do not delete Chromium/Safari cookie databases, Local Storage, IndexedDB, Service Worker data, cache folders, or whole browser profiles unless Kevin explicitly requests destructive browser-data cleanup and confirms the scope.

For environment fingerprint profiles, store only a sanitized local baseline by default. Keep region, timezone, locale/languages, proxy local ports, DNS resolver summary, ASN/provider, WebRTC verdicts, and PWR fingerprint verdicts when available. Redact or omit raw public IPs, LAN IPs, gateways, tailnet addresses, mDNS candidate values, browser profile names, raw PWR detection payloads, cookie contents, tokens, and secrets. Do not commit user-specific profile files to a public skill repo.

For official Claude Code privacy controls, prefer Anthropic's documented environment variables in `~/.claude/settings.json` under the top-level `env` key. These are low-risk config writes after backup, but they still require restarting Claude Code/terminal apps to ensure startup-read env values apply. Do not set `skipWebFetchPreflight` by default; it is a separate WebFetch safety-check opt-out with a security tradeoff, not part of `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`.

## Quick Audit

Run the bundled read-only audit first:

```bash
python3 "$SKILL_DIR/scripts/audit_claude_env.py" --audit
```

If `SKILL_DIR` is not set, resolve it from the skill folder path and run:

```bash
python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_claude_env.py --audit
```

Use the output to decide which workflow applies. If the audit finds sensitive keys, say only that the key exists and where it is configured, not its value.

The audit also reports official Claude privacy controls from the current process and `~/.claude/settings*.json`, including `DISABLE_TELEMETRY`, `DISABLE_ERROR_REPORTING`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, `DISABLE_FEEDBACK_COMMAND`, `CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY`, and `DO_NOT_TRACK`.

For network environment monitoring, run the read-only network audit:

```bash
python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_network_env.py
```

The CLI audit cannot see browser-only signals (WebRTC candidates, `Intl` locale, font probing, browser DNS). When those matter, point the user to the browser self-check at https://1pro.men/whoami/ and the manual checklist at https://blog.1pro.men/posts/claude-stability-checklist/. Do not open or fetch the page on the user's behalf unless asked.

When the user explicitly wants live public-IP and Claude reachability checks, add `--external`. To track whether the node region changes over time, append a history snapshot:

```bash
python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_network_env.py --external --append-history ~/.codex/network-env-history.jsonl
```

For a banned-account recovery self-check, add `--post-ban` so the audit prints browser site-data targets, manual cleanup reminders, and the five-site guide checklist:

```bash
python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_network_env.py --post-ban
```

For a reusable local environment baseline, create or read `~/.claude/session-env/environment-fingerprint-profile.md`. When answering from that file, say it is the user-confirmed local baseline and include its date before deciding whether a live re-check is needed.

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

7. If the user asks what the local timezone, exit region, DNS, IP, WebRTC, PWR fingerprint, browser language, or environment fingerprint baseline is, use the "Environment Fingerprint Profile" pattern. Prefer a user-confirmed sanitized baseline first, then run live checks only when freshness matters.

8. If the user asks for new-account usage takeaways, account warm-up, "养号期", or "指纹重置", use the "Account Stability and Fingerprint Reset Takeaways" pattern. Present these as operational stability heuristics, not as a guarantee that account risk is eliminated.

9. If the user says an account was banned, asks what to do after a ban, or asks to clear browser cookies, remove CC Switch, and re-check Claude App/Code, use the "Post-Ban Account Reset Self-Check" pattern. Keep it audit-first, make manual cookie/site-data actions highly visible, and do not perform destructive browser cleanup unless explicitly requested.

10. If the user calls something a Claude "skill" but it may be an installed artifact, verify the artifact class first:
   - skill folder
   - global npm or Homebrew CLI
   - app bundle
   - LaunchAgent
   - local data directory
   - log directory

Then clean the actual artifact class, not the label the user guessed.

11. If the user explicitly asks to delete official Claude App or Claude Code itself, use the "Uninstall Official Claude App and Claude Code" pattern below. This is a broader uninstall than route cleanup; include app bundles, package-manager installs, binaries, LaunchAgents, updater jobs, app support data, caches, preferences, saved state, and logs where present.

12. If Teamo or `com.claude-to-im.bridge` is mentioned, run a preservation check before and after cleanup: verify `teamo` still resolves, `~/.teamo` still exists, `~/.claude/projects` is not removed, and the bridge is still present/running when it was intentionally preserved.

13. If the user asks to clean local coding-agent configs based on request-chain trust rules, audit for four categories:
   - provider route overrides: `ANTHROPIC_BASE_URL`, `OPENAI_BASE_URL`, `api_base_url`, `baseUrl`, local proxy ports, third-party routers
   - request rewriting surfaces: Claude Code Router, provider transformers, gateway adapters, custom system-prompt/status-line commands
   - permission bypasses: `bypassPermissions`, skipped dangerous-mode prompts, unsafe host-header fallback
   - telemetry/debug residue: failed event files, debug logs, obsolete router logs, old DB/env backups containing key names

Clean only active-risk items by default. Preserve intentional tools and credentials unless the user asks to remove the tool itself.

14. If the user asks to enable official Claude Code privacy controls, use the "Official Claude Code Privacy Controls" pattern. Prefer the documented `env` block in `~/.claude/settings.json`, back up before editing, validate JSON after editing, and remind the user to restart Claude Code and terminal apps.

## Known Local Surfaces

Treat these as the high-yield inspection points:

- `~/.claude/settings.json`
- `~/.claude/settings.json` top-level `env` privacy controls:
  - `DISABLE_TELEMETRY`
  - `DISABLE_ERROR_REPORTING`
  - `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`
  - `DISABLE_FEEDBACK_COMMAND`
  - `CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY`
  - `DO_NOT_TRACK`
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
- manual browser site-data cleanup targets:
  - Chromium-family profile stores such as `~/Library/Application Support/Google/Chrome/*/Cookies`, `~/Library/Application Support/Google/Chrome/*/Network/Cookies`, `~/Library/Application Support/Google/Chrome/*/Local Storage`, `~/Library/Application Support/Google/Chrome/*/IndexedDB`, and equivalent Edge/Brave/Arc paths
  - Safari cookie and storage locations such as `~/Library/Containers/com.apple.Safari/Data/Library/Cookies` and `~/Library/Safari/LocalStorage`
- current process environment for `ANTHROPIC_*`
- listener on `127.0.0.1:15721`
- locale/timezone and browser-signal checks: `/etc/localtime`, `systemsetup -gettimezone` when sudo is available, `date`, browser language/locale settings, `~/Library/Fonts`, `/Library/Fonts`, and macOS system font locations
- network environment checks: `scutil --proxy`, `scutil --dns`, `route -n get default`, watched proxy ports such as `7890`, `7892`, `1080`, `8080`, `8888`, and browser-visible public IP/DNS/WebRTC/PWR checks
- sanitized local environment baseline: `~/.claude/session-env/environment-fingerprint-profile.md`

Route residue indicators include `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`, `ANTHROPIC_MODEL_NAME`, `OPENAI_BASE_URL`, `PROXY_MANAGED`, `127.0.0.1:15721`, `302ai-claude-code`, `claude-official`, `api.302.ai`, `glm-5.2`, `proxy_live_backup`, `claude-code-router`, `openrouter`, `anyrouter`, `api.deepseek.com`, `open.bigmodel.cn`, `teamocode.com`, and `code.newcli.com`.

Permission-risk indicators include `bypassPermissions`, `skipDangerousModePermissionPrompt`, and `dangerouslyAllowHostHeaderOriginFallback`.

Privacy-control indicators include `DISABLE_TELEMETRY`, `DISABLE_ERROR_REPORTING`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, `DISABLE_FEEDBACK_COMMAND`, `CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY`, `DO_NOT_TRACK`, `CLAUDE_CODE_ENABLE_FEEDBACK_SURVEY_FOR_OTEL`, and the separate setting `skipWebFetchPreflight`.

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
2. Create `~/Backups/cc-switch-delete-<timestamp>/` with `inventory/`, `files/`, and `removed/`.
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
   For the fixed cache/log candidates, use `scripts/trash_cleanup.py` (`plan`, then `run --confirm <code>` after the user approves the listed plan) instead of hand-written `mv`/`rm`; see 第五批 below. Run it from a plain terminal, not from the Claude Code session being cleaned.
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

### Official Claude Code Privacy Controls

Use when the user asks to enable Claude privacy controls, turn off telemetry/error reporting, block nonessential traffic, or mentions `DISABLE_TELEMETRY`, `DISABLE_ERROR_REPORTING`, or `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`. Official reference pages:

- `https://code.claude.com/docs/en/data-usage`
- `https://code.claude.com/docs/en/settings`

1. Back up `~/.claude/settings.json` before editing. If it does not exist, create it as a valid JSON object.
2. Merge these recommended values into the top-level `env` object:
   - `DISABLE_TELEMETRY: "1"`
   - `DISABLE_ERROR_REPORTING: "1"`
   - `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: "1"`
   - `DISABLE_FEEDBACK_COMMAND: "1"`
   - `CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY: "1"`
   - `DO_NOT_TRACK: "1"`
3. Do not set `skipWebFetchPreflight` unless the user specifically asks to disable the WebFetch domain safety check and accepts the security tradeoff.
4. Do not set auto-update or feature-flag-disabling variables as part of the privacy-control default unless the user asks for that narrower behavior.
5. Validate with `python3 -m json.tool ~/.claude/settings.json`.
6. Re-run `python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_claude_env.py` and confirm the "Official Claude Privacy Controls" section reports the expected controls.
7. Tell the user to restart Claude Code, Claude Desktop if relevant, and terminal sessions. Some settings reload on file change, but env-style controls are safest after process restart.
8. Clarify scope: these controls opt out of documented telemetry, error reporting, feedback, surveys, and nonessential traffic; they are not the same thing as zero data retention, browser cookie cleanup, or a full fingerprint reset.

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

### Environment Fingerprint Profile

Use when the user wants a reusable local baseline for questions such as "本机时区是什么", "出口/DNS/IP/WebRTC 是什么", "PWR 指纹是什么", or "按本机环境指纹汇总". This profile is for local Claude/Codex context, not for public repo publishing.

1. Generate the candidate from read-only sources:
   - `python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_network_env.py`
   - Add `--external` only when public-IP and Claude reachability probes are appropriate.
   - Prefer browser-side checks for DNS/WebRTC verdicts.
2. Sanitize before writing a profile:
   - Keep: country/region, timezone, IANA browser timezone, macOS locale/languages, browser language summary, local proxy ports, DNS resolver summary, network interface label, ASN/provider, IP version presence, WebRTC verdicts, and PWR fingerprint verdict/risk level when a browser check reports it.
   - Redact or omit: full public IPv4/IPv6 values, LAN IP, gateway, tailnet IPs, exact mDNS host candidates, browser profile names, raw PWR detection payloads, cookie/storage contents, tokens, OAuth values, API keys, and raw config secrets.
3. Store the sanitized profile at `~/.claude/session-env/environment-fingerprint-profile.md` unless the user specifies another local-only path.
4. When answering from this profile, say: "这是用户确认过的本机环境基线", include the confirmation date, and explain that IP/DNS/WebRTC/PWR can drift.
5. If live checks differ from the stored baseline, report the diff and ask before overwriting the baseline.
6. Never commit a user-specific baseline profile to the public skill repository; only commit the generic procedure.

Codex can automatically perform these read-only or low-risk setup steps after the user asks for an environment profile:

1. Run local audits for timezone, macOS locale, browser language preferences, proxy settings, system DNS, default route, watched proxy ports, and Claude reachability probes.
2. Create the local folder `~/.claude/session-env/` when missing.
3. Write a sanitized candidate profile to `~/.claude/session-env/environment-fingerprint-profile.md`.
4. Redact raw public IPs, LAN IPs, gateway addresses, tailnet addresses, exact WebRTC candidates, browser profile names, raw PWR detection payloads, and secrets before writing.
5. Re-read the written file and check that it contains no obvious raw IP or secret values.
6. Report the candidate as "待用户确认" until the user explicitly confirms it.

The user must manually perform or confirm these steps:

1. Confirm that the sanitized profile is accurate before it is treated as "用户确认过的本机环境基线".
2. Open browser-only checks such as `ip.net.coffee/claude`, `ippure.com/claude`, and `iplark.com` when DNS/WebRTC/PWR/IP risk must reflect the real browser, not the terminal.
3. Provide screenshots or page verdicts for browser-only values that automation cannot reliably read.
4. Restart browsers after timezone, language, proxy, extension, or cookie changes before trusting the baseline.
5. Approve any write to global Claude/Codex instruction files outside this profile path.
6. Approve any destructive cleanup, including deleting cookies, Local Storage, IndexedDB, browser extensions, browser profiles, Claude App, Claude Code, or CC Switch.

### Account Stability and Fingerprint Reset Takeaways

Use when the user asks how to reduce operational risk for a new Claude account, after a ban, or during an early account warm-up period. Treat these as user-provided stability heuristics and practical reminders, not as a bypass guarantee.

1. New-account early period:
   - For the first two weeks, use only the official Claude Desktop/App path and avoid standalone CLI use when following this strategy.
   - Do not use third-party clients such as OpenCode, OpenClaw, CraftAgent, or other unofficial wrappers during the early account phase.
   - Prefer platform subscription channels such as App Store or Google Play when the user explicitly asks for purchase-channel guidance; do not store payment details.
   - Start from the basic Pro tier and upgrade naturally after usage history exists; avoid abrupt heavy-tier behavior.
   - After upgrading to Max, keep the first two weeks conservative and avoid repeatedly hitting usage limits. If summarizing the user's heuristic, say "no more than about 3 limit hits" rather than treating it as an official threshold.
2. Usage rhythm:
   - Encourage a human-like work/rest rhythm; avoid continuous 24-hour high-load automation.
   - Do not share accounts. Shared use mixes devices, regions, browser fingerprints, and usage rhythms.
3. Network posture:
   - IP type is less important than stability and crowding. Avoid public, overused shared proxies.
   - In the early period, avoid frequent IP/country/ASN switching.
4. Fingerprint reset is the key post-ban step:
   - Before changing to a new account after a ban, complete the post-ban cleanup flow: browser site data, Claude extensions, Native Messaging manifests, official Claude App/Code residue, CC Switch, local auth/config/cache/log/telemetry residue, and browser-side network checks.
   - Treat `~/.claude/telemetry`, app caches, browser storage, Native Messaging, and third-party client configs as part of the fingerprint surface when the user asks for a reset.
   - Verify before reuse; do not assume uninstalling one app removed the whole fingerprint surface.
5. Warm-up window:
   - If the user asks for a timeframe, present the user's heuristic as about one month or after the first renewal, then relax constraints gradually.

Codex can automatically help by auditing local residue, checking active routes, listing third-party client configs, generating a sanitized environment baseline, and removing files only after explicit permission plus backup. The user must manually choose subscription channel, usage rhythm, account sharing behavior, browser-page verdicts, and whether to follow the early-period usage limits.

### Post-Ban Account Reset Self-Check

Use when the user says a Claude account was banned and asks for the three-step reset: clear browser cookies, remove CC Switch, and check/remove Claude Code terminal plus Claude Desktop App. This workflow is audit-first; it can identify cleanup targets, but cookie/site-data clearing and in-browser extension removal are manual unless Kevin explicitly requests destructive browser-data edits.

1. Start with read-only audits:
   - `python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_claude_env.py`
   - `python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_network_env.py --post-ban`
   - Add `--external` only when live public-IP and Claude reachability checks are appropriate.
2. Step 1, browser reset:
   - MANUAL REQUIRED: in every browser profile used with the banned account, clear site data/cookies/cache for `claude.ai`, `anthropic.com`, `console.anthropic.com`, and any Claude login/session helper domains.
   - MANUAL REQUIRED: remove or disable Claude/Anthropic browser extensions and session-key helper extensions tied to the banned account.
   - MANUAL REQUIRED: restart the browser after clearing, then re-run browser-side DNS/WebRTC/IP checks.
   - Do not delete a whole browser profile unless the user explicitly asks for that and a backup plan is clear.
3. Step 2, CC Switch:
   - If CC Switch is still present and the user has already said it can be deleted, use "Remove CC Switch App and State".
   - If the user only asked for audit, report whether `/Applications/CC Switch.app`, `~/.cc-switch`, Homebrew cask `cc-switch`, LaunchAgents, processes, and `127.0.0.1:15721` are present.
   - Preserve `com.claude-to-im.bridge`, Codex, and Teamo.
4. Step 3, Claude Code terminal and Desktop App:
   - If the user explicitly asks to delete official Claude App/Code, use "Uninstall Official Claude App and Claude Code".
   - If the user only asks to self-check, report `which -a claude`, `@anthropic-ai/claude-code`, `/Applications/Claude.app`, Chrome PWA shortcut, Claude Code URL Handler, Native Messaging manifests, Claude extensions, app support/cache/preferences/logs, and official Claude processes.
   - Preserve `~/.claude/projects`, `~/.teamo`, and `com.claude-to-im.bridge` unless separately requested.
5. After the three cleanup areas, open or instruct the user to open the five guide sites and record screenshots or key verdicts:
   - `https://ip.net.coffee/claude/`
   - `https://iplark.com/`
   - `https://net.coffee/`
   - `https://ippure.com/`
   - `https://cc.mastersgo.cc/`
   Treat `net.coffee` as a tool hub if it does not show a direct Claude result page; use its Claude/DNS/WebRTC tools as needed.
6. Report in four buckets:
   - automatically checked
   - manual action required
   - destructive cleanup performed with backup paths
   - remaining risks before using a new account
7. If the user says "指纹重置", treat it as the priority outcome: the local Claude/browser/client fingerprint surface should be clean or intentionally documented before the new account is used.

### Claude Network Environment Monitoring

Use when the user asks to check Claude network environment, IP purity, DNS leak, WebRTC leak, node region stability, or the "5 checks" from a Claude usage guide.

1. Run the local audit first:
   - `python3 ~/.agents/skills/claude-env-cleanup/scripts/audit_network_env.py`
   - Add `--external` only when live public-IP and Claude endpoint requests are appropriate.
   - Add `--post-ban` when the user wants the five-site post-ban guide checklist and browser site-data cleanup reminders.
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
   - PWR fingerprint warnings or mismatch flags from browser-side detection pages.
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
- official Claude privacy controls are present in `~/.claude/settings.json` under `env` when requested, and `skipWebFetchPreflight` is absent unless intentionally enabled
- CC Switch app/cask/data are absent when removal was requested
- coding-agent active configs no longer contain stale router endpoints, permission-bypass defaults, or unsafe Host Header fallback unless intentionally preserved
- `/etc/localtime` points to the intended timezone after timezone changes
- `~/Library/Fonts` user-installed fonts are absent or intentionally present after font-signal tests
- environment fingerprint profile is sanitized before being stored, does not contain raw public IPs, LAN/gateway/tailnet addresses, exact WebRTC candidates, raw PWR detection payloads, browser profile names, cookies, tokens, or secrets
- post-ban self-check reports browser cookie/site-data targets, makes manual browser cleanup actions explicit, confirms CC Switch state, confirms official Claude App/Code state, and records the five guide-site verdicts
- network audit reports expected proxy/DNS/default-route state, browser checks show no DNS/WebRTC leak, and history does not show unintended country/ASN drift when monitoring is enabled
- for app/CLI/browser-bridge uninstall, `/Applications/Claude.app`, `~/Applications/Chrome Apps.localized/Claude.app`, and `~/Applications/Claude Code URL Handler.app` are absent, `which -a claude` finds nothing, `npm list -g --depth=0` and `~/.npm/_npx` have no `@anthropic-ai/claude-code`, `~/Library/Caches/claude-cli-nodejs` is absent, Anthropic Native Messaging manifests are absent, Claude browser extension IDs are absent or intentionally preserved, and no official Claude process remains
- for Teamo and bridge preservation, `which -a teamo` or `/opt/homebrew/bin/teamo --version` still works, `~/.teamo` plus `~/.claude/projects` remain, and intentionally preserved `com.claude-to-im.bridge` remains loaded/running

When reporting results, separate:

- current facts verified in this run
- changes made
- backup paths
- residual risks or intentionally preserved routes


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

`executable: false`、`selected: false` 和 `review_only` 表示本轮仅供审阅。项目 ID 可用于生成临时测试工作区中的执行准备计划；清单本身不构成删除授权，也不是内容快照或恢复备份。清单本身不可执行；真实执行只有第五批的 `trash_cleanup.py`。`--audit` 与 `--format json` 不可组合，避免把纯元数据清单混同于详细诊断结果。

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

这是临时目录测试实现，不是已验收的生产清理器；测试上下文退出后临时备份也会删除，不能当成真实用户数据的恢复方案。`examples/cleanup-execution.fixture.json` 仅为假数据成功/失败回执示例。本模块本身不接触真实路径；第四批增加真实只读采集和路径预检，第五批另设仅限缓存/日志、移入废纸篓的真实入口。

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
- 退出码 2 表示有阻塞；0 仅表示已测范围内没有已知阻塞，仍需审阅、准确项目授权及重新采样。本报告本身不可执行；真实执行只有第五批的 `trash_cleanup.py`，它会重新采样并要求确认码。

本机预检报告属于本地用户资料，应写入工作区 `outputs/` 或指定本地目录，不提交到公开技能仓库。脚本 stdout 默认仅输出报告，不默认落盘。

## 第五批：缓存与日志移入废纸篓

`scripts/trash_cleanup.py` 是唯一会改动真实用户目录的入口，范围只有清单里的固定缓存/日志候选项。动作是移入废纸篓批次，不删除，不清空废纸篓。配置、认证、应用卸载、浏览器数据、共享会话、技能、Teamo、Claude-to-IM 和备份不能通过任何参数进入执行范围；命令行没有路径或根目录参数。

```bash
# 1. 只读：列出可处理项、不会处理的项、阻塞原因和确认码
python3 ~/.agents/skills/claude-env-cleanup/scripts/trash_cleanup.py plan

# 2. 用户审阅并明确同意后执行；可用 --ids 只选部分项目（plan 与 run 须一致）
python3 ~/.agents/skills/claude-env-cleanup/scripts/trash_cleanup.py run --confirm <确认码>

# 3. 撤回一个批次
python3 ~/.agents/skills/claude-env-cleanup/scripts/trash_cleanup.py restore --batch <批次名>
```

- 确认码由所选项目的 ID、路径、元数据摘要和父目录身份算出。目录内容或选择一变，旧确认码即失效，须重新 `plan` 并重新取得用户同意。AI 不得自行生成同意或跳过审阅。
- 进程采集不完整，或检测到 Claude、Teamo、Claude-to-IM、共享 Claude 状态的使用者时拒绝执行，执行中每一项之前重新检测。进程列表在两次采样之间变化会使样本不完整，此时最多重采 12 次，只接受完整且无相关进程的样本。本工具不终止任何进程，须由用户自行退出后重试。正在使用这些目录的 Claude Code 不能清理自身，应在普通终端运行。
- 移动是同一卷内的原子重命名，移入 `~/.Trash/ClaudeCleanup-<UTC 时间>-<确认码>/<项目 ID>`，批次内写入 `receipt.json`。跨卷时直接停止，没有“复制再删除”的退路。移动后核对实际移入对象的元数据摘要。
- 目录超过 10,000 个条目或 10 秒扫描上限、含符号链接父路径、硬链接、特殊文件或他人所有的对象时，该项列入“不会处理”并留在原处，不提高上限。
- 废纸篓批次就是恢复副本，没有另外的复制备份。清空废纸篓后无法撤回；访达的“放回原处”对这些项目不可用，撤回请用 `restore`。
- `restore` 的目标位置来自固定项目表，不取自回执文本。原路径已被重新创建（Claude 下次启动通常会重建缓存）时不覆盖，该项保留在废纸篓并标为 `source_recreated_not_overwritten`；废纸篓内副本被改动时同样不恢复。
- 终端没有“完全磁盘访问权限”时 macOS 可能拒绝访问 `~/.Trash`，此时报 `trash_unavailable_check_full_disk_access`，不改用其他位置。
- 任一错误立即停止，回执逐项记录 `moved`、`not_moved` 等状态。已移走的项不自动回滚。

验证范围：`test_trash_cleanup.py` 在临时目录内覆盖移动、撤回、保护项拒绝、符号链接、进程阻塞、跨卷、确认码失效和原路径重建。真实用户目录上只验证过“Claude 运行时拒绝执行”，尚未做过一次完整的真实移动与撤回验收。
