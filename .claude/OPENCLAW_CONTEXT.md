# OpenClaw Context — FugginOld/ai-config

## Architecture

OpenClaw is the orchestration layer. `FugginOld/ai-config` is the brain.
Matt Pocock's skills (`mattpocock/skills`) are the methodology engine.

```text
FugginOld/ai-config
        │
        ├── global/          ← AGENTS.md, CLAUDE.md, token rules
        ├── core/            ← workflow-core, workflow-gates, agent-routing
        ├── openclaw/        ← THIS FILE, skill-map, channel-map, prompts
        └── templates/       ← CONTEXT.md, PR template, ADR template
                │
                ▼
        OpenClaw Orchestration
                │
                ├── Loads skill-map.md → routes to Pocock skills
                ├── Loads channel-map.md → selects workflow
                └── Reads CONTEXT.md from target repo
                         │
                         ▼
                 Target coding repos
                  (FugginOld/*)
```

## What OpenClaw Does NOT Need to Build

The following workflows are already provided by `mattpocock/skills`.
Do NOT duplicate them in `ai-config/workflows/`:

| OpenClaw Channel | Pocock Skill | Slash Command |
| --- | --- | --- |
| coding | tdd | `/tdd` |
| diagnose | diagnose | `/diagnose` |
| architecture | zoom-out + improve-codebase-architecture | `/zoom-out` |
| issue-breakdown | to-issues | `/to-issues` |
| requirements | grill-me / grill-with-docs | `/grill-me` |
| documentation | write-a-skill + custom | `/write-a-skill` |

## What `ai-config` Owns

- Token efficiency rules (`global/CLAUDE.md`)
- Agent routing and escalation logic (`core/agent-routing.md`)
- Org-specific coding standards (`global/AGENTS.md`)
- `CONTEXT.md` template (consumed by Pocock skills)
- PR/issue templates
- `bootstrap.ps1` (deploys Pocock skills + config to each repo)

## Instruction Load Order for OpenClaw Agents

1. `ai-config/global/AGENTS.md`
2. `ai-config/global/CLAUDE.md` (token efficiency)
3. `ai-config/core/workflow-core.md`
4. `ai-config/core/agent-routing.md`
5. `ai-config/openclaw/skill-map.md`
6. Target repo `CONTEXT.md`
7. Selected Pocock skill (e.g. `/tdd`)

## OpenClaw Execution Rules

1. Read repo `CONTEXT.md` before any edit.
2. One issue or task at a time.
3. Small, reversible changes only.
4. Run available checks after edits.
5. Report commands run and results.
6. Summarize modified files.
7. No architecture changes before behavior works.
8. No bypassing existing tests or CI.
9. Require approval before destructive changes.

## Permissions

```text
Auto-allowed:
- read repo files
- write files inside target repo
- run non-destructive local commands
- create draft issues
- create draft PR summaries

Require approval:
- git push
- deleting files
- force resets
- dependency upgrades
- editing CI/CD config
- modifying secrets
```
