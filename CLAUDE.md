<!-- The constitution: loaded in full every prompt, so it holds must-know-only.
     How to think here, never how to do a task — task knowledge lives in skills.
     This file grows ONLY by explicit user confirmation; skills grow through evolve
     (skill-manager/references/evolve.md). Keep it thin: a rule earns its place here
     only when every session needs it. Design record: docs/design/agentic-base.md. -->

# init-configurator — constitution

**Consult the skill index before acting.** Skills carry the HOW; each fires by shape:

- `workflow` — any code written, changed, or resumed: the SWE loop (orient → plan →
  implement → verify → document → commit, NEVER push → reflect). Its references cover
  scaling past one context and rot-checking. Start here when unsure what to do next.
- `bootstrap` — phase 0: starting, scaffolding, or adopting a project or stack.
- `skill-manager` — skill hygiene and the genome's lifecycle: a lesson landing, a skill
  added/split/merged, genes moving between repos. References: evolve, absorb, authoring.
- `socials` — posting, launching, promoting, or making anything findable. The human
  always posts. References: LinkedIn, GitHub, visuals.

Working without a matching skill? Log one line in `docs/state/miss-log.md`, keep working.

**The line:** skills know HOW, tools know WHETHER, `project.yaml` records WHAT. Never
move knowledge from markdown into code constants.

## The rules (binding, not style)

- **Gates all green before every commit** — the set CI runs: `ruff check`,
  `ruff format --check`, `mypy src`, `pytest --cov` (≥90%), `initc lint-paths`,
  `initc validate`, and the schema-drift check. `project.yaml` declares the core tasks
  (`initc run test | lint | typecheck`); the pre-commit and CI configs are the full set.
- **Commit at chunk boundaries; NEVER push.** The user pushes, or explicitly says push.
  Public repo: an unpushed mistake is free, a pushed one is not.
- **A skill edit is a code change** — reviewed diff, never silent. This constitution grows
  only when the user confirms it; a lesson learned goes through evolve into a skill.
- **The user owns every line.** Public showcase repo — code quality is the product;
  nothing merges that the user cannot explain. Approving fast without understanding is a
  bug: slow down.
- **Root-relative paths only** (`initc lint-paths` enforces it); **no global installs**
  (deps live in ./.venv). The env rule: the same turn code first reads a new var, declare
  it in `project.yaml` and re-run `initc env` — doctor's env-sync fails on drift.
- **Post drafts live in `docs/posts/` (gitignored). No em dashes (U+2014) in post text.**

## Where things live

- `project.yaml` — WHAT: stacks, gates-as-tasks, env contract, path-lint config.
- `docs/structure.md` — the module map: every file in one line.
- `docs/design/agentic-base.md` — the design record: the line, the organs, honest limits.
- `docs/state/` — `now.md` (where the project is) → `roadmap.md` (next) → `log.md` (was).
- Brain note (machine-local): `G:\PythonProjects\_for_me\The Brain v2\knowledge\projects\init-configurator.md` — read on session start.
