# Log

> One entry per chunk, newest first: date · what happened · what it proved or changed.

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
