# 0002 — Ship the genome inside the package (`initc spawn`)

Date: 2026-07-11 · Status: accepted

## Context

The first spawn (traffic-rl, 2026-07-10) was executed by hand: copy `.claude/skills/`,
copy the standards, seed `docs/`. It worked, and it surfaced the friction that the
child needed init-configurator itself installed from a sibling checkout. With the repo
going public, one command should hand a new project the whole starter. The absorb
skill's rule was: promote spawn to a command once the by-hand shape is proven. It is.

## Decision

- The transferable genome ships as **package data** under
  `src/init_configurator/genome/`: the three portable skills (`workflow`,
  `skill-manager`, `bootstrap` — with their references), the standards
  (`.gitattributes`, `.gitignore`), and the `docs/` templates (vision, state, posts).
- **`initc spawn <path>` is additive by default.** A file that already exists is
  reported as "kept" and not overwritten — same rule beacons always had. This is why the
  tool needs no interview: it cannot destroy. WHETHER to install the genome into a repo
  that already has one is a judgment call, so it lives in the bootstrap skill's interview
  (step 0b), not in the tool.
  - **Amended 2026-07-11 — `--force`:** an existing child that wants the base's newer
    skills can pass `--force`, which overwrites existing files **under `.claude/skills/`
    only**, still never deleting. Docs and standards stay additive so a filled-in
    `vision.md` or a custom `.gitignore` is never clobbered — the value users accumulate
    lives there, and losing it is the one destruction worth ruling out by construction.
    "Cannot destroy" becomes "cannot destroy what you own, and never silently": `--force`
    is opt-in and its every change shows in `git diff`.
- **`project.yaml` and `project-base` are not in the genome.** They are per-project:
  `describe`/`bootstrap` write the manifest; `beacons.py` templates the project skill
  from it.
- **Dotfiles ship `_`-prefixed** (`_gitignore` → `.gitignore` on spawn): a real
  `.gitignore`/`.gitattributes` inside the package tree would apply to THIS repo's own
  files, and dotfiles are easy for packaging to drop silently.
- **The genome and `.claude/skills/` are held byte-identical by a test**
  (`test_genome.py`). The repo dogfoods exactly what it ships; two copies of markdown
  would otherwise drift with no import error to catch it. `project-base` is exempt
  (repo-specific by design).
- The genome directory is **path-lint exempt** in `project.yaml`, inheriting
  `.claude/`'s exemption: its container paths document other repos, not this one.

## Consequences

- One command starts a project from the public repo:
  `uvx --from git+https://github.com/Stepkar2004/init-configurator initc spawn my-project`.
- The `local` dependency-group friction from the first spawn dissolves once the repo is
  public (children pin `init-configurator @ git+https://...`).
- Editing a shipped skill now REQUIRES mirroring it into the genome in the same commit —
  the drift test makes forgetting impossible.
- `initc absorb` stays a by-hand procedure until its shape is proven, same bar spawn had.
