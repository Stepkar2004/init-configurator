"""Context beacons: the agent-facing constitution every managed project carries.

The discovery chain a coding agent walks in a freshly cloned project:

1. CLAUDE.md or AGENTS.md at the root — whichever the user's agent reads
   natively is the PRIMARY (the full constitution); the other is a one-line
   POINTER to it (the ``agent`` choice at bootstrap time decides which);
2. the constitution names the skills (``.claude/skills/`` — ``workflow`` first)
   and points at ``project.yaml`` as the single source of truth.

There is no separate project skill: the constitution IS the always-loaded
instruction layer, and the repo's growing lessons live in the ``workflow`` skill
(through the evolve procedure), not in a per-repo skill file.

These functions are the TEMPLATE SOURCE the bootstrap skill materializes into a
new project during phase 0. A fresh repo gets the full ``constitution`` inline; a
repo that already has a CLAUDE.md gets ``pointer_block`` APPENDED, never
overwritten. All of it is owned by the project afterwards.
"""

from typing import Literal

from init_configurator.manifest import Manifest

PrimaryChoice = Literal["agents", "claude"]


def context_beacons(
    manifest: Manifest, agent: PrimaryChoice, *, brain_note: str | None = None
) -> dict[str, str]:
    """Return ``{filename: content}`` for a FRESH repo's CLAUDE.md and AGENTS.md.

    The primary file carries the full constitution; the other is a one-line
    pointer. For a repo that already has a CLAUDE.md, use ``pointer_block``
    instead and append it — never overwrite what the user wrote.
    """
    primary, pointer = (
        ("CLAUDE.md", "AGENTS.md") if agent == "claude" else ("AGENTS.md", "CLAUDE.md")
    )
    return {
        primary: constitution(manifest, brain_note=brain_note),
        pointer: _pointer_content(manifest, target=primary),
    }


def constitution(manifest: Manifest, *, brain_note: str | None = None) -> str:
    """The full downstream constitution — CLAUDE.md/AGENTS.md for a fresh repo.

    Always loaded in full, so it holds must-know-only: the skill index, the line,
    the binding rules, and the declared tasks. Generic on purpose ("the user"),
    so it reads the same for whoever clones the base.
    """
    tasks = "\n".join(
        f"- `initc run {task}` — `{command}`"
        for stack in manifest.stacks
        for task, command in stack.tasks.items()
    )
    tasks_section = tasks or "- (no tasks declared yet — add them under stacks[].tasks)"
    brain_line = (
        f"\n\nBrain note (machine-local): {brain_note} — read on session start."
        if brain_note
        else ""
    )
    return f"""\
<!-- The constitution: loaded in full every prompt, so it holds must-know-only.
     How to think here, never how to do a task - task knowledge lives in .claude/skills/.
     This file grows ONLY by explicit user confirmation; skills grow through evolve. -->

# {manifest.project.name} — constitution

{manifest.project.description}

**Consult the skill index before acting.** Skills carry the HOW (`.claude/skills/`):

- `workflow` — any code written, changed, or resumed: the SWE loop (orient → plan →
  implement → verify → document → commit, NEVER push → reflect). Start here when unsure.
- `bootstrap` — phase 0: starting, scaffolding, or adopting a project or stack.
- `skill-manager` — skill hygiene and the genome's lifecycle (evolve, absorb, authoring).
- `socials` — posting, launching, or making the project findable. The human always posts.

**The line:** skills know HOW, tools know WHETHER, `project.yaml` records WHAT.

## The rules (binding, not style)

- **`project.yaml` is the single source of truth** — stacks, tasks, env vars, and data
  paths are declared there. Read it before changing setup; change IT, not around it.
- **Gates green before every commit; commit at chunk boundaries; NEVER push.** The user
  pushes, or explicitly says push. Run the declared gates (tasks below); `initc doctor`
  diagnoses the machine, and every problem it prints comes with its fix.
- **Root-relative paths only** (`initc lint-paths` enforces it); **no global installs**
  (deps live in ./.venv or ./node_modules). The env rule: the same turn code first reads
  a new var, declare it in `project.yaml` and re-run `initc env`.
- **A skill edit is a code change** — reviewed diff, never silent. A lesson learned goes
  through evolve (`skill-manager`) into a skill; this constitution grows only when the
  user confirms it.
- Post drafts live in `docs/posts/` (gitignored). No em dashes in post text.

## Tasks (from project.yaml — run from any subfolder)

{tasks_section}{brain_line}
"""


def pointer_block() -> str:
    """A short marked block to APPEND to a repo's existing CLAUDE.md/AGENTS.md.

    For a repo that already has a constitution of its own: never overwrite it,
    add these pointers so an agent finds the tool and the skills. The HTML
    comment makes the block identifiable and removable.
    """
    return """\

<!-- init-configurator: appended by bootstrap. Safe to edit or remove. -->
## Project setup (init-configurator)

- **`project.yaml` is the single source of truth** for stacks, tasks, env, and data paths.
  Run gates with `initc run <task>`; `initc doctor` diagnoses setup.
- **Read `.claude/skills/workflow/SKILL.md` before writing code** (the SWE loop); see also
  `bootstrap` (scaffolding), `skill-manager` (skill hygiene), `socials` (shipping visibly).
- Root-relative paths only (`initc lint-paths`); no global installs; commit at chunk
  boundaries and NEVER push — the human pushes.
"""


def _pointer_content(manifest: Manifest, target: str) -> str:
    return f"""\
# {manifest.project.name}

Agent instructions live in [{target}]({target}) — read that file first; this one
exists only so every coding agent finds its way there.
"""
