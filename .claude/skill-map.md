# Skill Map — OpenClaw → FugginOld/ai-config

Maps OpenClaw channels and task types to the correct skill source.

## Engineering Skills (from mattpocock/skills)

| Task | Slash Command | When to Use |
| --- | --- | --- |
| TDD implementation | `/tdd` | Any new feature or bug fix requiring code changes |
| Structured debugging | `/diagnose` | Failing tests, broken commands, CI failures, dep issues |
| Architecture review | `/zoom-out` | Before touching unfamiliar code or starting a large task |
| Architecture improvement | `/improve-codebase-architecture` | After multiple TDD cycles, when modules feel shallow |
| Requirement alignment | `/grill-me` | New feature idea, ambiguous requirement, design decision |
| Requirement alignment (with docs) | `/grill-with-docs` | Same as above but when ADRs or docs exist to reference |
| Issue breakdown | `/to-issues` | Convert findings or PRD into GitHub-ready issues |
| PRD generation | `/to-prd` | Turn a feature idea into a structured product requirement |
| Issue triage | `/triage` | Label and prioritize open issues |
| Token compression | `/caveman` | Long sessions where context overhead is high |

## Config Skills (from ai-config)

| Task | Source File | When to Use |
| --- | --- | --- |
| AI workflow wizard | `skills/ai-config/ai-workflow-wizard/SKILL.md` | Repo scan + minimal interview that outputs a plan only |
| Agent routing / escalation | `core/agent-routing.md` | Deciding which model or tool handles a task |
| Workflow gates | `core/workflow-gates.md` | Go/no-go checks before proceeding to next step |
| Token efficiency | `global/CLAUDE.md` | Always loaded; governs model selection and scope |
| Coding standards | `global/AGENTS.md` | Always loaded; governs style and review rules |
| New repo context | `templates/CONTEXT.md` | Bootstrapped into each new repo; never auto-overwritten |
| PR summary | `templates/pull_request_template.md` | After completing a task, before pushing |
| ADR creation | `templates/adr-template.md` | When an architecture decision is made during a session |

## Path Aliases

These are the actual file paths in `ai-config` that map to OpenClaw's
expected workflow names from `OPENCLAW_CONTEXT.md`:

| OPENCLAW_CONTEXT.md expects | Actual ai-config path |
| --- | --- |
| `global/global-ai-workflow.md` | `core/workflow-core.md` |
| `global/token-efficiency.md` | `global/CLAUDE.md` |
| `global/coding-standards.md` | `global/AGENTS.md` |
| `workflows/tdd.md` | `mattpocock/skills` → `/tdd` |
| `workflows/diagnose.md` | `mattpocock/skills` → `/diagnose` |
| `workflows/zoom-out.md` | `mattpocock/skills` → `/zoom-out` |
| `workflows/to-issues.md` | `mattpocock/skills` → `/to-issues` |
| `skills/tdd-implementation/` | `mattpocock/skills` → `/tdd` |
| `skills/diagnose/` | `mattpocock/skills` → `/diagnose` |
| `skills/repo-review/` | `mattpocock/skills` → `/zoom-out` + `/improve-codebase-architecture` |
