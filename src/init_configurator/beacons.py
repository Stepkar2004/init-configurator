"""Context beacons: the agent-instruction files scaffolded at the project root.

Two files, one relationship: whichever the user's coding agent reads natively
is the PRIMARY (full instructions); the other is a one-line POINTER to it.
Claude Code reads CLAUDE.md, most other agents read AGENTS.md — the ``agent``
choice at init time decides which is which. Content is written once and owned
by the project afterwards; init never overwrites it.
"""

from typing import Literal

from init_configurator.manifest import Manifest

PrimaryChoice = Literal["agents", "claude"]


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
