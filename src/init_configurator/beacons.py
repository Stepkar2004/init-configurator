"""Context beacons: the agent-facing files every managed project carries.

The discovery chain a coding agent walks in a freshly cloned project:

1. CLAUDE.md or AGENTS.md at the root — whichever the user's agent reads
   natively is the PRIMARY (full instructions); the other is a one-line
   POINTER to it (the ``agent`` choice at bootstrap time decides which);
2. the primary points at the instantiated project skill
   (``.claude/skills/project-base/SKILL.md``) — workflow, ground rules, and
   the repo's growing lessons;
3. the skill points at ``project.yaml`` — the single source of truth.

These functions are the TEMPLATE SOURCE the bootstrap skill materializes into
a new project during phase 0. All of it is written once and owned by the
project afterwards — never overwrite an existing beacon.
"""

from datetime import date
from typing import Literal

from init_configurator.manifest import Manifest

PrimaryChoice = Literal["agents", "claude"]

SKILL_PATH = ".claude/skills/project-base/SKILL.md"


def context_beacons(manifest: Manifest, agent: PrimaryChoice) -> dict[str, str]:
    """Return ``{filename: content}`` for CLAUDE.md and AGENTS.md."""
    primary, pointer = (
        ("CLAUDE.md", "AGENTS.md") if agent == "claude" else ("AGENTS.md", "CLAUDE.md")
    )
    return {
        primary: _primary_content(manifest),
        pointer: _pointer_content(manifest, target=primary),
    }


def _primary_content(manifest: Manifest) -> str:
    tasks = "\n".join(
        f"- `initc run {task}` — `{command}`"
        for stack in manifest.stacks
        for task, command in stack.tasks.items()
    )
    tasks_section = tasks or "- (no tasks declared yet — add them under stacks[].tasks)"
    return f"""\
# {manifest.project.name} — agent instructions

{manifest.project.description}

Read the project skill FIRST: [{SKILL_PATH}]({SKILL_PATH}) — the setup
workflow, ground rules, and this repo's accumulated lessons live there.

## Ground rules

- **project.yaml is the single source of truth.** Runtimes, dependency files, tasks,
  env vars, and data paths are declared there — read it before changing setup, and
  change IT rather than working around it.
- **Root-relative paths only.** Resolve every path from the project root (the folder
  containing project.yaml). Never hardcode absolute paths — path-lint rejects them.
- **No global installs.** Dependencies live inside the project (./.venv, ./node_modules).
- If setup misbehaves, run `initc doctor` before debugging by hand.

## Tasks (from project.yaml — work from any subfolder)

{tasks_section}
"""


def _pointer_content(manifest: Manifest, target: str) -> str:
    return f"""\
# {manifest.project.name}

Agent instructions live in [{target}]({target}) — read that file first; this one
exists only so every coding agent finds its way there.
"""


def project_skill(manifest: Manifest) -> dict[str, str]:
    """The canonical downstream project skill — this function IS the template.

    Every project scaffolded by init-configurator gets its own copy; each copy
    evolves with its repo (the lessons section) and never syncs back here.
    Divergence is the design.

    Not to be confused with init-configurator's own checked-in
    ``.claude/skills/project-base/SKILL.md``, which is this repo's evolved copy
    and is not what downstream repos receive.
    """
    tasks = ", ".join(sorted({name for stack in manifest.stacks for name in stack.tasks}))
    description = (
        f"Manifest-driven setup (initc), conventions, and growing lessons for "
        f"{manifest.project.name}; applies to every work session in this repo."
    )
    content = f"""\
---
name: project-base
description: {description}
---
# project-base — {manifest.project.name}

Instantiated from init-configurator on {date.today().isoformat()}. This copy EVOLVES
with this repo and never syncs back to the template — divergence is the design.
A lesson worth keeping goes through the evolve procedure
(`skill-manager/references/evolve.md`): procedure, not anecdote, appended below
as a reviewed diff.

## The setup workflow (everything derives from project.yaml)

1. `initc doctor` — is this machine ready? Three-state report, every problem
   comes with its fix.
2. `initc run install` — installing is a declared task like any other; it
   creates the in-project environment (./.venv or ./node_modules).
3. `initc run <task>` — run a declared task from anywhere in the tree
   (declared here: {tasks or "none yet"}).
4. `initc env` — regenerate .env.example after changing the env contract.
5. `initc lint-paths` — no absolute paths, ever. `pre-commit install` wires it
   into every commit via `.pre-commit-config.yaml`; nothing enforces it in CI
   until you add it to your workflow.

## Ground rules

- project.yaml is the single source of truth: to change setup, change IT.
- Root-relative paths only — use `project_root()` / `path_to()` from the
  `init_configurator` package instead of building paths by hand.
- No global installs: dependencies live in ./.venv or ./node_modules.
- The env rule: the same turn code first reads a new env var, declare it in
  project.yaml and re-run `initc env` — doctor's env-sync check fails on drift.
- Generated files (.env.example) say so in their header — edit the manifest,
  not the artifact. Everything else is yours to edit.
- Commit at chunk boundaries; NEVER push — the human pushes, or explicitly
  says push. An unpushed mistake is free; a pushed one is not.
- Post drafts live in `docs/posts/` (gitignored). No em dashes (U+2014) in
  post text, ever: use commas, colons, or parentheses. The `socials` skill owns
  the posting workflow (decide -> optimize -> draft -> post; the human posts).

## Lessons (append one line per real session: date · lesson; prune when stale)

<!-- self-evolution starts here -->
"""
    return {SKILL_PATH: content}
