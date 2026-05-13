# Prompt: Repo Review

# Channel: architecture

# Skills: /zoom-out, /improve-codebase-architecture

Load the following in order:

1. This repo's CONTEXT.md
2. Any ADRs in docs/adr/ (if present)
3. README.md

Then run /zoom-out.

Return:

- High-level summary of what this repo does and how it's structured
- Identified shallow modules (lots of interface, little value)
- Test coverage gaps
- Documentation drift (docs that don't match code)
- Missing ADRs for decisions that were clearly made
- Top 3 recommended next actions, ranked by impact

Do NOT edit any files.
Do NOT propose implementation yet.
