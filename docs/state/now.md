# Now

> Updated at every chunk boundary (gates pass → this file + log.md → commit).
> Cold start reads: `../vision.md` → this file → `roadmap.md`.

**As of 2026-07-11 (published; socials skill authored; project-base retired):**

The genome survived its first real generation and then shed a vestige. A child ran phase 0
on it and evolved it — nested-skill consolidation, a `workflow` skill, authoring standards,
never-push and posts conventions — and those genes were absorbed back here as reviewed
diffs. The genome ships inside the package: `initc spawn <dir>` copies it into any project,
additive-only, `--force` refreshes a child's skills (ADR 0002).

**`project-base` is retired (ADR 0003).** It predated `workflow`; its jobs moved to their
real homes — session-wide rules and the module-map pointer into the constitution
(`CLAUDE.md`, now denser and human-gated), lessons into the `workflow` skill via evolve,
the module map into `docs/structure.md`. Teach-me and the cold-start block are gone.
`beacons.py` now templates a downstream **constitution** (full inline, or a marked pointer
block appended to an existing CLAUDE.md) instead of a project skill; bootstrap's interview
gained the CLAUDE.md-style question. Skills here are exactly the
transferable four — `workflow`, `skill-manager`, `socials`, `bootstrap` — mirrored
byte-identical in `src/init_configurator/genome/` (test-enforced; repo set == shipped set).

- Published at github.com/Stepkar2004/init-configurator (2026-07-11); repo description +
  14 topics applied for discoverability.
- `socials` skill authored (2026-07-11, raw) from a four-source research pass. The launch
  post is ready to post (`docs/posts/2026-07-11-the-amputation.md`, local); posting is the
  owner's to do.
- `docs/vision.md` still unfilled — waiting on the owner.
- `initc absorb` as a command: still by hand, same promotion bar spawn had.

**Next action:** owner posts the launch reflection; propagate the project-base retirement
into the spawned children via `initc spawn . --force` + a cleanup pass; then rot-check
pass #1 (roadmap step 4).
