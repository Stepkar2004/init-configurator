# ADR 0001 — Amputate the scaffolder; skills lead, tools verify

- **Status:** accepted, executed 2026-07-10
- **Decided:** 2026-07-09, mid-phase-7, by Stepan
- **Full rationale:** [../design/agentic-base.md](../design/agentic-base.md)

## Context

The repo had grown into a template scaffolder: `initc init` wrote pyproject/biome/
tsconfig/Dockerfile contents from Python string constants. Across two adversarial
reviews, **every defect found lived in that generation layer** (CRLF, corepack,
unreachable carets, pip dev-groups) and **none in the verification layer** (manifest,
doctor, path-lint, env contract, runner). The knowledge was also stored where no agent
could read it — string constants inside a tool that exists to make repos legible to
agents.

## Decision

**Skills know HOW. Tools know WHETHER. `project.yaml` records WHAT.**

- Delete `presets/`, `local_mode.py`, `docker_mode.py`, `initc init`; rename
  `languages.py` → `runtimes.py`, keeping only per-language checks.
- Generation moves to `.claude/skills/bootstrap/` + per-stack references, executed by an
  agent against official ecosystem creators, current at run time.
- Installing becomes a declared task (`initc run install`); `initc describe` (new)
  drafts a manifest from an existing repo — the empty-folder assumption dies.
- The manifest's consumerless `docker:` section is removed; docker knowledge lives in
  `bootstrap/references/docker.md`.

## Consequences

- Adding a language = one registry entry + one reference file, not a preset folder with
  a shelf life.
- The verified facts from the hardening work survive as dated reference knowledge
  instead of rotting constants.
- Skill edits become the system's evolution mechanism, so every one goes through a
  human-reviewed diff (see the `evolve` skill) — self-modification with immunity.
- Git history keeps the scaffolder era; `docs/reviews/` remains the evidence trail.
