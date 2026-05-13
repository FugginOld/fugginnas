# Channel Map — OpenClaw Channels → Skills

## coding

**Purpose**: Direct implementation, bug fixes, refactors, file edits.

Load order:

1. `CONTEXT.md` (repo root)
2. `core/workflow-core.md`
3. `/tdd` (mattpocock)

Entry prompt:

```text
Load CONTEXT.md. Use /tdd. One issue at a time. Vertical slices only.
Write a failing test first. Implement minimum code to pass. Report result.
```

---

## diagnose

**Purpose**: Failing tests, broken commands, lint errors, CI failures, dep problems.

Load order:

1. `CONTEXT.md` (repo root)
2. `core/workflow-gates.md`
3. `/diagnose` (mattpocock)

Entry prompt:

```text
Load CONTEXT.md. Use /diagnose.
Build a feedback loop first. Do not edit code until you have a
repeatable failure signal. Run safe local checks only.
Report findings before proposing fixes.
```

---

## architecture

**Purpose**: Repo structure review, module design, long-term improvements.

Load order:

1. `CONTEXT.md` (repo root)
2. `docs/adr/` (if present)
3. `/zoom-out` then `/improve-codebase-architecture` (mattpocock)

Entry prompt:

```text
Load CONTEXT.md and any ADRs in docs/adr/.
Use /zoom-out to understand the current structure.
Do not edit files yet. Return findings.
Then use /improve-codebase-architecture to identify shallow modules
and high-leverage improvement opportunities.
```

---

## issue-breakdown

**Purpose**: Convert analysis or PRD into GitHub-ready issues.

Load order:

1. `CONTEXT.md` (repo root)
2. `templates/ai-task.md`
3. `/to-issues` (mattpocock)

Entry prompt:

```text
Load CONTEXT.md and the issue template from templates/ai-task.md.
Use /to-issues. Each issue must be independently shippable.
Include: title, problem, acceptance criteria, suggested files,
validation command. No broad issues. One behavior per issue.
```

---

## requirements

**Purpose**: Requirement alignment before any implementation begins.

Load order:

1. `CONTEXT.md` (repo root)
2. `/grill-me` or `/grill-with-docs` (mattpocock)

Entry prompt:

```text
Load CONTEXT.md. Use /grill-me.
Ask questions one at a time. Recommend an answer for each.
Do not proceed to implementation until every branch is resolved.
Update CONTEXT.md with any new terminology agreed on.
```

---

## wizard

**Purpose**: Read-only repo scan + plan generation, then hand off to an execution channel after approval.

Load order:

1. `CONTEXT.md` (repo root)
2. `/ai-workflow-wizard` (ai-config)

Entry prompt:

```text
Load CONTEXT.md. Run /ai-workflow-wizard.
Scan and plan only. Do not edit files.
Return one plan in the wizard output format, using <proposed_plan> when supported.
After plan approval, switch to the appropriate execution channel (coding/diagnose/architecture).
```

---

## documentation

**Purpose**: README, HOWTO, setup guides, usage docs, ADR authoring.

Load order:

1. `CONTEXT.md` (repo root)
2. `templates/adr-template.md` (if architecture decision)
3. `/write-a-skill` if creating a new skill

Entry prompt:

```text
Load CONTEXT.md. Update documentation to match current implementation.
Keep docs concise, procedural, and accurate.
Do not add claims not supported by the code.
List all files changed.
```

---

## maintenance

**Purpose**: Recurring cleanup, dep checks, formatting, dead-file review.

Load order:

1. `CONTEXT.md` (repo root)
2. `core/agent-routing.md`
3. `/diagnose` (mattpocock) for any failing checks

Entry prompt:

```text
Load CONTEXT.md. Run only safe, non-destructive local checks.
Report: unused files, stale deps, formatting violations, test gaps.
Do not modify files without listing changes first.
```
