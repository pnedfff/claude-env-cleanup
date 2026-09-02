---
name: claude-env-cleanup
description: Audit and safely clean Claude Desktop, Claude Code, Anthropic browser bridges, CC Switch, related local routes, privacy controls, and network signals on macOS. Use for Claude 环境检查, Claude 残留清理, CC Switch 清理, Claude 卸载, ANTHROPIC_* route audits, DNS/WebRTC checks, and Claude privacy-control reviews. The standalone cleanup.py and double-click launcher are the primary implementation; Codex is optional.
---

# Claude Env Cleanup

## Core rule

The standalone `cleanup.py` program is the source of truth. Ordinary users run `双击启动.command`; they do not need Codex. When this skill is used, call the same program instead of recreating cleanup commands by hand.

## Safety contract

- Default to a read-only audit.
- Never print raw secrets, tokens, API keys, OAuth values, refresh tokens, cookies, or complete private configuration values.
- Before any cleanup, show the exact targets and obtain two explicit confirmations.
- Cleanup moves items to a timestamped recovery folder under `~/Backups/claude-env-cleanup/`; it does not permanently delete them.
- Never hard-code a username or a path such as `/Users/<name>`. Resolve the current home directory dynamically.
- Do not automatically remove browser cookies, Local Storage, IndexedDB, Service Worker data, entire browser profiles, system fonts, unrelated proxies, or unrelated developer tools.
- Preserve user project data such as `~/.claude/projects` and `~/.claude/skills`.
- Add `--external` to network audits only when the user explicitly wants external public-IP or reachability requests.

## Standard workflows

Read-only check and report:

```bash
python3 "$SKILL_DIR/cleanup.py" --check
```

Preview safe cleanup without changes:

```bash
python3 "$SKILL_DIR/cleanup.py" --safe-clean --dry-run
```

Preview deep cleanup without changes:

```bash
python3 "$SKILL_DIR/cleanup.py" --deep-clean --dry-run
```

Actual cleanup is interactive and requires two confirmations:

```bash
python3 "$SKILL_DIR/cleanup.py" --safe-clean
python3 "$SKILL_DIR/cleanup.py" --deep-clean
```

For detailed standalone audits, reuse:

```bash
python3 "$SKILL_DIR/scripts/audit_claude_env.py"
python3 "$SKILL_DIR/scripts/audit_network_env.py"
```

The default network audit is local and read-only. Use `--external` only with explicit permission.

## Reporting

Report separately:

- facts verified in the current run;
- changes made;
- the recovery-backup path;
- items skipped because they were in use or required administrator access;
- intentionally untouched browser or project data.

After implementation changes, run `python3 -m unittest discover -s tests -v` and a fake-HOME `--deep-clean --dry-run` before describing the launcher as safe.
