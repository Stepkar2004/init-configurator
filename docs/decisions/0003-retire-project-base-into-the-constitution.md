# 0003 — Retire `project-base` into the constitution

Date: 2026-07-11 · Status: accepted

## Context

`project-base` was a skill from before `workflow` existed: it bound every session with
the gates, conventions, module map, and a Lessons section. Once `workflow` (the SWE loop,
absorbed and consolidated 2026-07-11) and `skill-manager` (lifecycle, evolve, the
miss-log) landed, `project-base` was doing three jobs that already had better homes:

- **Session-wide rules** belong in the constitution (`CLAUDE.md`), the one file loaded in
  full every prompt. A rule in a skill only fires if the skill triggers; a rule in the
  constitution is always in context.
- **The module map** is `docs/structure.md`, kept honest by rot-check.
- **Lessons** belong in `workflow` (or the relevant skill) through the evolve procedure —
  that is the point of the genome. In the base, the mirror test then ships an evolved
  lesson to every child; base-learning IS genome-learning.

It also carried a **teach-me protocol** and a **cold-start reading order**. The reading
order duplicated `workflow`'s orient step; the teach-me protocol was never load-bearing.
Keeping `project-base` meant a fourth job — a name collision with `beacons.py`, the real
downstream template — that already cost one confused spawn round-trip.

## Decision

- **Delete the `project-base` skill.** The base's top-level set is now exactly the four
  transferable skills (`workflow`, `skill-manager`, `socials`, `bootstrap`), and the
  repo's skill set equals the shipped set (a test enforces it — no repo-only skill can
  creep back).
- **`CLAUDE.md` is the constitution**: the skill index, the line, the binding rules
  (gates, never-push, reviewed skill diffs, owns-every-line, paths/env, posts), and a
  "where things live" map. It is denser than before and holds what `project-base` held.
- **Two growth doors, both human-gated.** Skills grow through evolve (reviewed diff;
  default destination `workflow`). **The constitution grows ONLY on explicit user
  confirmation** — never appended to silently. A lesson lands in a skill; a rule every
  session must obey is *proposed* as a CLAUDE.md edit and waits for the user.
- **Downstream projects get a constitution, not a project skill.** `beacons.py` templates
  it two ways, chosen in the bootstrap interview: a fresh repo gets `constitution()`
  inline; a repo that already has a CLAUDE.md gets a short marked `pointer_block()`
  APPENDED, never overwritten — invading a stranger's constitution costs their context
  budget on every prompt.
- **Teach-me protocol and the cold-start block are gone** — the first was never
  load-bearing; the second is `workflow`'s orient step.

## Consequences

- One less skill to keep at altitude; the collision between the repo's self-copy and
  `beacons.py` disappears, so the spawn CLI hint that warned about it is removed too.
- `beacons.py` no longer emits a `project_skill()`; it emits the constitution (and the
  append variant). `SKILL_PATH` is gone.
- Children of the base evolve their lessons into `workflow`, which they already carry —
  learning no longer needs a bespoke per-repo skill file.
- The constitution is now the single human-gated document. That is the intended
  bottleneck: rules that bind every session should be hard, and visible, to change.
