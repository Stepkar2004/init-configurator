---
name: project-base
description: Portfolio-project conventions, self-evolving lessons, and the teach-me protocol for this repo. Applies to every work session here; also use when Stepan says he doesn't understand something or asks to be taught a concept.
---
# project-base — init-configurator (CANONICAL TEMPLATE — other repos instantiate this)

Instantiated: 2026-07-09 (this copy is the template source). Every copy EVOLVES with its
repo and never syncs back — divergence is the design, not drift.

## Conventions (from TheBrain2 `knowledge/projects/job-first-pivot.md`)

1. **Stepan owns every line.** AI drafts; nothing merges to main until he can explain the
   change. If he approves fast without understanding, slow him down — that's the
   argmech/VC2 debt lesson. Interviewers probe; the code must be HIS.
2. **Root-relative paths only.** No `G:\...`, no `/home/...`, no hardcoded absolutes.
   Everything resolves from project root. (This repo builds the linter that enforces it.)
3. **No global installs.** Deps live in the project (venv/npm local) or in Docker.
4. **Ship visibly:** a milestone isn't done until README shows it (GIF/screenshot) and a
   LinkedIn reflection draft exists. Demo before polish.
5. On session start: read the brain note pointer in CLAUDE.md for current project state.

## Teach-me protocol (optional; fires when Stepan says "I don't understand X" / "teach me X")

Explain PROPERLY, not fast: (1) the concept from first principles, no jargon assumed;
(2) a minimal generic example; (3) the same idea as it appears in THIS repo's code;
(4) common pitfalls/misconceptions; (5) check understanding with 1-2 questions back.
For deep topics, suggest a fresh side session dedicated to teaching — keeps this
session's context lean (his token-hygiene preference). Teaching writes NOTHING to the
repo unless he asks.

## Lessons (append one line per real session: date · lesson; prune when stale)

<!-- self-evolution starts here -->
