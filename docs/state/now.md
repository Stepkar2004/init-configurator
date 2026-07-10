# Now

> Updated at every chunk boundary (gates pass → this file + log.md → commit).
> Cold start reads: `../vision.md` → this file → `roadmap.md`.

**As of 2026-07-10:**

The pivot to the agentic base is EXECUTED. The scaffolder (presets, local mode, docker
mode, `initc init`) is amputated; the tool is verification-only
(`validate · doctor · env · run · lint-paths · schema · describe`), the genome is in
place (7 skills under `.claude/skills/`), and all gates are green.

- `docs/vision.md` exists but is unfilled — waiting on Stepan.
- The skills are structurally complete but young: their references carry facts verified
  2026-07; none has yet evolved from real downstream use.
- Nothing is published; no remote configured.

**Next action:** roadmap step 1 — a first downstream project spawns FROM this genome
(new repo, per the `absorb` skill's spawn procedure; work never happens in here). Its
frictions come back as `evolve` diffs. Then remote + publish. Stepan still owes the
amputation review (owns-every-line rule) and `vision.md`.
