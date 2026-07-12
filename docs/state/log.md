# Log

> One entry per chunk, newest first: date · what happened · what it proved or changed.

- **2026-07-11 · Retired `project-base` into the constitution (ADR 0003).** The skill
  predated `workflow`; its jobs moved to their real homes — session-wide rules and the
  module-map pointer into `CLAUDE.md` (now a denser, human-gated constitution), lessons
  into `workflow` via evolve, the map into `docs/structure.md`. Teach-me and the
  cold-start block deleted. `beacons.py` lost `project_skill()`/`SKILL_PATH` and now
  templates a downstream constitution two ways — full inline, or a marked `pointer_block`
  APPENDED to an existing CLAUDE.md, never overwriting (don't invade a stranger's
  constitution, it costs their context budget). Bootstrap's interview gained the
  CLAUDE.md-style question. The spawn CLI hint about the old name
  collision is gone with the collision. `test_genome` now asserts repo skill set ==
  shipped set (no repo-only skill can creep back). The base's genome no longer names
  another project. Gates green.
- **2026-07-11 · `initc spawn --force` + README restructure.** Spawn stayed additive by
  default; `--force` now overwrites existing files under `.claude/skills/` ONLY (docs and
  standards untouched, nothing ever deleted), so an already-spawned child can pull the
  base's newer skills with `git diff` showing every change. `SpawnedFile.created` became a
  three-state `outcome` (added/kept/replaced); `uvx` caches, so the docs now teach
  `--refresh`. README reordered to the reader's path — Quickstart → skills → tools →
  manifest, each with a one-line "why" before the "what". ADR 0002 amended; the "cannot
  destroy" invariant refined to "cannot destroy what you own, and never silently."
  125 tests, gates green.
- **2026-07-11 · The socials skill: ship-visibly gets its HOW.** Authored from a
  four-source research pass run as parallel subagents: the longform-factory skill's
  stage architecture (VideoCreator2), a live read of ~40 real LinkedIn posts
  (fold verified at ~140-220 chars by screenshot), and two web sweeps (LinkedIn
  algorithm 2025-26, GitHub discoverability). One top-level skill — decide → optimize →
  draft → post, the human always posts — with lazy references: linkedin.md, github.md,
  visuals.md. Dated facts separated from mechanism facts everywhere (platform knowledge
  rots faster than code). Mirrored into the genome (now four shipped skills); README
  genome section became per-skill bullets. Found in passing: the repo's GitHub topics
  are EMPTY — the "why doesn't my repo show in search" answer.
- **2026-07-11 · Rot-check finding #1: CI actions off deprecated Node 20.** Bumped
  `actions/checkout@v4 → v7` (floating major tag exists) and `astral-sh/setup-uv@v5 →
  v8.3.2` (exact pin — no floating v8 tag, the absorbed lesson applied). Both now run
  Node 24. Also de-named the base to "the user" (a cloner is not the author; authorship
  keeps the real name, spelling fixed to Karapetyan) and gave bootstrap an owner-identity
  interview step. README leads with a summary now.
- **2026-07-11 · First absorb + spawn shipped + published.** The first child (traffic-rl)
  evolved the genome through real phase-0 use; its genes came back as reviewed diffs:
  nested-skill consolidation (7 top-level → 4: workflow with scale/rot-check as
  references, skill-manager with evolve/absorb/authoring as references), never-push and
  posts conventions, Actions-pinning and `local`-group facts into python.md. The genome
  now ships as package data with `initc spawn` (additive-only, never overwrites; ADR
  0002) — verified end-to-end from an installed wheel. `.claude/skills` ↔ genome held
  byte-identical by test. beacons downstream template carries the new conventions.
  120 tests, ~94% coverage, gates green. Pushed public to
  github.com/Stepkar2004/init-configurator.

- **2026-07-10 · Publish prep staged.** Decision: the genome gets one real downstream
  validation (a project spawned from this base into its own repo) before publicizing.
  README gained an honest Status section; announcement draft staged locally
  (gitignored, with the publish checklist).

- **2026-07-10 · The amputation.** Deleted presets/, local_mode, docker_mode,
  `initc init`; `languages.py` became verification-only `runtimes.py`; added
  `initc describe` (draft a manifest from an existing repo) + tests; installing became
  a declared task (`initc run install`). Built the genome: project-base, bootstrap
  (+5 references), evolve, skill-manager, scale, absorb, rot-check. Added
  vision/state/decisions docs layer. All template knowledge moved from Python constants
  into agent-readable references. Gates green (107 tests, coverage 93.8%),
  verified by a fresh-context Opus review (verdict: ship).
- **2026-07-09 · The pivot decision.** Stopped phase 7 mid-implementation: the repo had
  become "choose a stack, it builds a kit" — not the self-evolving base intended.
  Diagnosis: across two adversarial reviews, every defect lived in the generation
  layer, none in verification. Decision recorded in `../design/agentic-base.md`;
  uncommitted docker/version work reverted, its verified facts preserved in
  `bootstrap/references/`.
- **2026-07-09 and before · The scaffolder era.** Manifest, local mode, path-lint,
  doctor, docker mode built and hardened per `../reviews/`. History preserved in git;
  the reviews remain the record of why the pivot happened.
