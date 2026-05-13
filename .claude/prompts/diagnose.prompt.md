# Prompt: Diagnose

# Channel: diagnose

# Skills: /diagnose

Load this repo's CONTEXT.md.

Run /diagnose.

Rules:

- Build a repeatable failure signal FIRST. Do not proceed without one.
- Run only safe, non-destructive local commands.
- Change one variable at a time when testing hypotheses.
- Do not modify source files until findings are confirmed.

Return:

- Feedback loop established (what signal you found)
- Root cause hypothesis list (3–5 items, falsifiable)
- Which hypothesis was confirmed
- Exact files involved
- Proposed fix (one change only)
- Regression test to write before applying the fix
