# FugginOld — Claude Code Global Instructions

# Managed by FugginOld/ai-config — do not edit directly in target repos

# Bootstrap: bootstrap.ps1 | Last updated: 2026-05-09

---

## Agent Handoff

### On session start / before any task:

1. Retrieve session context:
   `ctx_search(queries: ["recent work", "current task", "blockers"])`
2. Retrieve durable memory:
   `mempalace_search("project: <repo-name> recent decisions")`
3. State your understanding of current state in one sentence before proceeding.

### Before ending any task / before /compact:

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

- **Default model:** Sonnet — edits, tests, refactoring, explanations
- **Haiku:** rename, format, lookup, repetitive ops only
- **Opus:** complex multi-file architecture or deep cross-system debug only
- **`/effort low`** for straightforward tasks
- **`/caveman`** for implementation tasks (75% token reduction)
- New session for unrelated tasks
- Check `/context` and `/usage` before large tasks
- Install code intelligence plugins for typed languages — Claude skips unrelated files

### Compact Instructions

Run `/compact` proactively — before overload, not after.

When compacting, preserve:

- current task goal | files changed | commands run | failing tests + errors | decisions | next actions

Drop:

- old exploration paths | repeated logs | irrelevant discussion

---

## Context-Mode Rules (MANDATORY)

See global `~/.claude/CLAUDE.md` for full routing table.

**Bash ONLY for:** `git`, `mkdir`, `rm`, `mv`, `cd`, `ls`, `npm install`, `pip install`
Everything else → sandbox via `ctx_execute` or `ctx_batch_execute`

- NEVER read large files raw — use `ctx_execute_file`
- NEVER run analysis loops with Read — write a script, log only the result
- Raw HTML never enters context — always `ctx_fetch_and_index` → `ctx_search`
- After resume/compact: `ctx_search(sort: "timeline")` before asking the user
- Health checks: run `context-mode doctor` (CLI) plus in-session smoke (`ctx_doctor`, `ctx_search(sort: "timeline")`, trivial `ctx_batch_execute`)
- If `Dynamic require of "node:fs" is not supported` appears, run `/ctx-upgrade`, restart session, then re-run smoke checks

---

## Workflow

### Development Process

For non-trivial changes:

1. Inspect CONTEXT.md and repo instructions first
2. Diagnose before implementing — provide exact file names, not repo-wide scans
3. Use context-mode for scans, grep, test output, architecture review
4. Break large work into scoped issues
5. TDD: reproduce → failing test → minimal fix → verify
6. Run targeted checks; broader validation only if shared behavior changes
7. Pre-filter logs: `pnpm test 2>&1 | grep -A5 -E "FAIL|ERROR" | head -120`

### Verification Targets

Before starting, tell Claude: expected outputs, exact test names, pass conditions. Prevents correction loops.

### TDD Loop

1. Reproduce or define expected behavior
2. Write/adjust a failing test
3. Implement minimal fix
4. Run targeted test
5. Refactor only after green tests
6. Run final verification

---

## CI Workflow Gates

Claude owns gates: **Context (1), Plan (2), Architecture Check (6), Final Review (8)**.

| Gate | Command | Pass condition |
| --- | --- | --- |
| 1 — Context | `/grill-with-docs` | Scope defined, no unknown domain terms, no arch conflicts |
| 2 — Plan → Issue | `/to-prd` + `/to-issues` | One independently completable issue, clear acceptance criteria |
| 6 — Architecture Check | `/improve-codebase-architecture` | No unnecessary abstraction, no duplication, no ADR conflicts |
| 8 — Final Review | `/diagnose` | Correctness verified, missing tests flagged, risks documented |

**Escalate from Codex → Claude only for:** unclear architecture, conflicting tests, ambiguous requirements, multi-subsystem changes, ADR needed.
**Do NOT escalate for:** syntax errors, normal test failures, formatting, import fixes, boilerplate.

---

## Output Format

Every non-trivial response must end with:

```text
Changed files:
Commands run:
Tests passing:
Known risks:
Next step:
```

---

## Skills

| Skill | Activate | Purpose |
| --- | --- | --- |
| `ai-workflow-wizard` | `/ai-workflow-wizard` | Read-only repo scan + minimal interview → plan only |
| `caveman` | `/caveman` | 75% token reduction |
| `grill-me` | `/grill-me` | Pre-task alignment |
| `grill-with-docs` | `/grill-with-docs` | Plan vs CONTEXT.md + ADRs |
| `write-a-prd` | `/write-a-prd` | Structured PRD |
| `tdd` | `/tdd` | Red-green-refactor loop |
| `diagnose` | `/diagnose` | Disciplined debug loop |
| `write-a-skill` | `/write-a-skill` | Create new skills |
| `git-guardrails` | `/git-guardrails-claude-code` | Block destructive git ops |

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
- If context exceeds 70%, compact the chat.

Verification:
- Add or update targeted tests.
- Run only the relevant test file first.
- Run broader tests after the targeted test passes.
```

---

## What to Avoid

- Don't use `.claudeignore` — use the `deny` permissions block instead.
- Don't install every available plugin — unused tools add constant overhead.
- Don't default to Opus for routine tasks — Sonnet covers 90%+ of daily work.
- Don't let bad file-reading paths run to completion — interrupt and rewind early.
- Don't ask for repo-wide scans — provide exact file names.

---

## Memory

### claude-mem

For explicit retrieval (token-efficient two-step):

1. `search(query="...", limit=10)` → get observation IDs
2. `get_observations(ids=[...])` → fetch only what's relevant

`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` — claude-mem handles all session memory.

### MemPalace

On session start: `mempalace_search("project: <repo-name> recent decisions")`

Key tools:

- `mempalace_search("query")` / `mempalace_search("query", wing="<repo-name>")`
- `mempalace_diary_write` — decisions, completions, blockers, handoffs
- `mempalace_kg_query` — knowledge graph | `mempalace_status` — overview

Only invoke on history/context queries — not on every response.
