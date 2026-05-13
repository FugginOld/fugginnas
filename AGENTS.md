# FugginOld — Codex CLI Global Instructions (AGENTS.md)

# Managed by FugginOld/ai-config — do not edit directly in target repos

# Bootstrap: bootstrap.ps1 | Last updated: 2026-05-09

---

## Agent Handoff

### On session start / before any task:

1. Retrieve session context:
   `ctx_search(queries: ["recent work", "current task", "blockers"])`
   (context-mode Codex adapter)
2. Retrieve durable memory:
   `mempalace_search("project: <repo-name> recent decisions")`
3. State your understanding of current state in one sentence before proceeding.

### Before ending any task:

1. `mempalace_diary_write` — record what was done, decisions made, open blockers
2. `ctx_index` any output worth preserving
3. End every response with a one-paragraph handoff summary:
   - What was completed | What is next | Any blockers

### Cross-agent handoff:

- Outgoing: `mempalace_diary_write` with tag `handoff:<target-agent>`
- Incoming: `mempalace_search("handoff:<source-agent>")` before first response
- Confirm: "Resuming from [source] handoff: [summary]"

---

## Token Efficiency

- **Default model:** `o4-mini` — edits, tests, refactoring, explanations
- **`o4-mini`:** rename, format, lookup, repetitive ops
- **`o3`:** complex multi-file architecture or deep cross-system debug only
- Use `--no-projectdoc` flag on simple tasks (skips AGENTS.md injection overhead)
- New session for unrelated tasks
- Check token usage before large tasks

### Compact Instructions

Compact proactively — before overload, not after.

When compacting, preserve:

- current task goal | files changed | commands run | failing tests + errors | decisions | next actions

Drop:

- old exploration paths | repeated logs | irrelevant discussion

---

## Context-Mode Rules (MANDATORY)

<!-- Source: https://github.com/mksglu/context-mode -->
<!-- Installed via: npm install -g context-mode@latest -->
<!-- Note: Codex CLI has no hook support — routing is manual, no session tracking -->

### Routing — when to use which tool

| Situation | Use |
| --- | --- |
| Analyze / explore / summarize a file | `ctx_execute_file(path, language, code)` |
| Run shell commands, grep, queries | `ctx_execute(language: "shell", code: "...")` |
| Multiple commands + queries at once | `ctx_batch_execute(commands, queries)` |
| Fetch a URL | `ctx_fetch_and_index(url, source)` then `ctx_search(queries)` |
| Store output for later retrieval | `ctx_index(content, source)` |
| Search indexed knowledge | `ctx_search(queries: ["q1", "q2"])` |

**Bash ONLY for:** `git`, `mkdir`, `rm`, `mv`, `cd`, `ls`, `npm install`, `pip install`
Everything else → sandbox via `ctx_execute` or `ctx_batch_execute`

### Key rules

- NEVER read large files raw — use `ctx_execute_file` instead
- NEVER run analysis loops with multiple Read tool calls — write a script, log only the result
- Raw HTML never enters context — always `ctx_fetch_and_index` → `ctx_search`
- No automatic session restore on Codex — query MemPalace for prior context instead
- Write all artifacts to FILES, never inline — return file path + one-line description

### context-mode health check

- CLI check: `context-mode doctor`
- In-session smoke: `ctx_doctor`, `ctx_search(sort: "timeline")`, and a trivial `ctx_batch_execute(...)`
- If you see `Dynamic require of "node:fs" is not supported`: run `/ctx-upgrade`, restart session, then re-run smoke tests

### Blocked — do not use

- `curl`/`wget` in shell — dumps raw HTTP into context; use `ctx_fetch_and_index(url, source)`
- Inline HTTP (`node -e "fetch(..."`, `python -c "requests.get(..."`) — use `ctx_execute(language, code)`
- Direct web fetching — raw HTML can exceed 100 KB; always `ctx_fetch_and_index` → `ctx_search`

### Windows notes

- Sandbox uses bash — PowerShell cmdlets fail; wrap with `pwsh -NoProfile -Command "..."`
- Sandbox CWD is temp dir — always convert relative paths to absolute
- Windows paths in sandbox: `X:\path` → `/x/path` (lowercase, no `/mnt/`)
- Always double-quote paths containing spaces

---

## Workflow

### Development Process

For non-trivial changes:

1. Inspect CONTEXT.md and AGENTS.md first
2. Diagnose before implementing — provide exact file names, not repo-wide scans
3. Use context-mode for scans, grep, test output, architecture review
4. Break large work into scoped issues — one branch per issue
5. TDD: reproduce → failing test → minimal fix → verify
6. Run targeted checks; broader validation only if shared behavior changes
7. Pre-filter logs: `npm test 2>&1 | grep -A5 -E "FAIL|ERROR" | head -120`

### AI Workflow Wizard

If the user asks to "scan this repo", "assess this repo", or "run the AI workflow wizard", run `/ai-workflow-wizard` first:

- Scan and plan only (read-only); do not edit files.
- Ask only the minimum questions needed.
- Output one plan and wait for approval before executing via `/tdd` or `/diagnose`.

### Verification Targets

Before starting, tell the agent: expected outputs, exact test names, pass conditions. Prevents correction loops.

### TDD Loop

1. Reproduce or define expected behavior
2. Write/adjust a failing test
3. Implement minimal fix
4. Run targeted test
5. Refactor only after green tests
6. Run final verification

---

## CI Workflow Gates

Codex owns gates: **TDD Loop (4), Diagnose (5), Local CI (7)**.

| Gate | Actions | Pass condition |
| --- | --- | --- |
| 4 — TDD Loop | Write failing test → minimal fix → confirm pass → refactor | Tests exist or justified; no scope creep |
| 5 — Diagnose | Validate expected behavior, edge cases, regressions, assumptions | No unresolved blockers; critical paths tested |
| 7 — Local CI | `git status`, `npm test`, `npm run lint`, `pytest`, `ruff check .`, `mypy .` | All checks pass or failures documented |

**Escalate to Claude only for:** unclear architecture, conflicting tests, ambiguous requirements, multi-subsystem changes, ADR needed.
**Do NOT escalate for:** syntax errors, normal test failures, formatting, import fixes, boilerplate.

---

## Output Format

Every response must end with:

```text
Changed files:
Commands run:
Tests passing:
Known risks:
Next step:
```

---

## Optimal Prompt Template

```text
Task: Fix [specific bug] in [specific files].

Scope:
- Start with: [file1], [file2]
- Do not scan the whole repo.
- Only read additional files if they are imported.

Token discipline:
- Keep command output short.
- Filter test output to failures only.
- Summarize findings before editing.

Verification:
- Add or update targeted tests.
- Run only the relevant test file first.
- Run broader tests after the targeted test passes.
```

---

## What to Avoid

- Don't use `.claudeignore` — use the `deny` permissions block instead.
- Don't install every available plugin — unused tools add constant overhead.
- Don't default to `o3` for routine tasks — `o4-mini` covers 90%+ of daily work.
- Don't let bad file-reading paths run to completion — interrupt and rewind early.
- Don't ask for repo-wide scans — provide exact file names.
- For custom git workflows only: set `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1` to remove built-in git instructions.

---

## Memory (MemPalace MCP)

<!-- Source: https://github.com/MemPalace/mempalace -->
<!-- Venv: ~/.venvs/mempalace/ | MCP config: ai-config/memory/mempalace/codex-mcp.json -->

On session start: `mempalace_search("project: <repo-name> recent decisions")`

Key tools:

- `mempalace_search("query")` / `mempalace_search("query", wing="<repo-name>")`
- `mempalace_diary_write` — decisions, completions, blockers, handoffs
- `mempalace_kg_query` — knowledge graph | `mempalace_status` — overview

Only invoke on history/context queries — not on every response.
