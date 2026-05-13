# FugginOld — GitHub Copilot Global Instructions

# Managed by FugginOld/ai-config — do not edit directly in target repos

# Bootstrap: bootstrap.ps1 | Last updated: 2026-05-09

# Deploy target: .github/copilot-instructions.md in each repo

---

## Agent Handoff

### On session start / before any task:

1. Retrieve durable memory via MCP:
   `mempalace_search("project: <repo-name> recent work blockers")`
2. Retrieve recent decisions:
   `mempalace_search("project: <repo-name> recent decisions")`
3. State your understanding of current state in one sentence before proceeding.

### Before ending any task:

1. `mempalace_diary_write` — record what was done, decisions made, open blockers
2. End every response with a one-paragraph handoff summary:
   - What was completed | What is next | Any blockers

### Cross-agent handoff:

- Outgoing: `mempalace_diary_write` with tag `handoff:<target-agent>`
- Incoming: `mempalace_search("handoff:<source-agent>")` before first response
- Confirm: "Resuming from [source] handoff: [summary]"

---

## Token Efficiency

- **Default model:** GPT-4o — edits, tests, refactoring, explanations
- **GPT-4o mini:** rename, format, lookup, repetitive ops only
- **GPT-4o (extended context):** complex multi-file architecture or deep debug only
- Only invoke MemPalace MCP on history/context queries — not on every response

### Compact Instructions

When compacting, preserve:

- current task goal | files changed | commands run | failing tests + errors | decisions | next actions

Drop:

- old exploration paths | repeated logs | irrelevant discussion

---

## Workflow

### Development Process

For non-trivial changes:

1. Inspect CONTEXT.md and repo instructions first
2. Diagnose before implementing — provide exact file names, not repo-wide scans
3. Break large work into scoped issues
4. TDD: reproduce → failing test → minimal fix → verify
5. Run targeted checks; broader validation only if shared behavior changes
6. Pre-filter logs: `pnpm test 2>&1 | grep -A5 -E "FAIL|ERROR" | head -120`

### Verification Targets

Before starting, state expected outputs, exact test names, and pass conditions. Prevents correction loops.

### TDD Loop

1. Reproduce or define expected behavior
2. Write/adjust a failing test
3. Implement minimal fix
4. Run targeted test
5. Refactor only after green tests
6. Run final verification

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

- Don't ask for repo-wide scans — provide exact file names.
- Don't default to extended-context models for routine tasks — GPT-4o covers 90%+ of daily work.
- Don't let bad file-reading paths run to completion — interrupt and rewind early.
- Don't install every available plugin — unused tools add constant overhead.
- Provide verification targets up front to prevent correction loops.

---

## Memory (MemPalace MCP)

<!-- Source: https://github.com/MemPalace/mempalace -->
<!-- MCP config: ai-config/memory/mempalace/vscode-mcp.json → .vscode/mcp.json -->
<!-- Requires: VS Code Copilot in Agent mode -->

On session start: `mempalace_search("project: <repo-name> recent decisions")`

Key tools:

- `mempalace_search("query")` / `mempalace_search("query", wing="<repo-name>")`
- `mempalace_diary_write` — decisions, completions, blockers, handoffs
- `mempalace_kg_query` — knowledge graph | `mempalace_status` — overview

Only invoke on history/context queries — not on every response.
