"""Copy the packaged genome into a target project, additively.

Spawn is the mechanical half of inheritance; the judgment half stays with the
agent running the absorb skill's spawn procedure (review what changed, record
lineage, run bootstrap next). By default this module only ADDS files: a target
file that already exists is reported as kept and never touched. ``force_skills``
lets the base's version win for existing SKILL files only -- docs and standards
stay additive so a filled-in template (a real vision.md, a custom .gitignore) is
never clobbered -- and even then it only rewrites files the genome ships, never
deleting anything the target added on its own.

The genome ships inside the package (``init_configurator/genome/``):

- ``skills/``    -> ``.claude/skills/`` in the target
- ``standards/`` -> the target root (dotfiles ship ``_``-prefixed: a real
  .gitignore inside the package would apply to THIS repo's own tree)
- ``docs/``      -> ``docs/`` in the target

``project.yaml`` and the ``project-base`` skill are deliberately absent:
``describe``/``bootstrap`` write those fresh per project (``beacons.py`` is
their template source).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path, PurePosixPath
from typing import Literal

from init_configurator.textfile import write_text_lf

#: genome top-level folder -> where its contents land, relative to the target
_DESTINATIONS = {
    "skills": PurePosixPath(".claude/skills"),
    "standards": PurePosixPath(),
    "docs": PurePosixPath("docs"),
}

#: only files under here are eligible for --force overwrite (see module docstring)
_SKILLS_DEST = _DESTINATIONS["skills"]

#: names that cannot exist verbatim inside the package (see module docstring)
_RENAMES = {"_gitignore": ".gitignore", "_gitattributes": ".gitattributes"}

#: what happened to one genome file in the target
Outcome = Literal["added", "kept", "replaced"]


class SpawnError(Exception):
    """Spawn cannot proceed; the message says why and what to do instead."""


@dataclass(frozen=True)
class SpawnedFile:
    """One genome file's fate in the target: added, kept as-is, or replaced."""

    target: PurePosixPath
    outcome: Outcome


def genome_root() -> Traversable:
    """The packaged genome directory (works installed and editable alike)."""
    return files("init_configurator").joinpath("genome")


def spawn_genome(target_dir: Path, *, force_skills: bool = False) -> list[SpawnedFile]:
    """Copy every missing genome file into ``target_dir``.

    Existing files are kept, except that ``force_skills`` overwrites existing
    files under ``.claude/skills/`` with the base's version when they differ.
    """
    if target_dir.exists() and not target_dir.is_dir():
        raise SpawnError(
            f"{target_dir} is a file - spawn needs a project folder "
            f"(an existing one, or a path to create)"
        )
    results: list[SpawnedFile] = []
    for source, relative in sorted(_genome_files(), key=lambda pair: str(pair[1])):
        destination = target_dir / relative
        if destination.exists():
            results.append(_reconcile(source, destination, relative, force_skills))
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        write_text_lf(destination, source.read_text(encoding="utf-8"))
        results.append(SpawnedFile(relative, "added"))
    return results


def _reconcile(
    source: Traversable, destination: Path, relative: PurePosixPath, force_skills: bool
) -> SpawnedFile:
    """Decide the fate of a genome file whose target already exists."""
    if not (force_skills and relative.is_relative_to(_SKILLS_DEST)):
        return SpawnedFile(relative, "kept")
    incoming = source.read_text(encoding="utf-8")
    if destination.read_text(encoding="utf-8") == incoming:
        return SpawnedFile(relative, "kept")
    write_text_lf(destination, incoming)
    return SpawnedFile(relative, "replaced")


def _genome_files() -> Iterator[tuple[Traversable, PurePosixPath]]:
    """Yield ``(packaged file, target-relative path)`` for the whole genome."""
    for top in genome_root().iterdir():
        if not top.is_dir():
            continue  # e.g. a stray __init__ artifact; the genome is folders only
        base = _DESTINATIONS.get(top.name)
        if base is None:
            raise SpawnError(
                f"packaged genome has an unmapped folder '{top.name}' - "
                f"spawn.py's _DESTINATIONS must name where it lands"
            )
        yield from _walk(top, base)


def _walk(node: Traversable, prefix: PurePosixPath) -> Iterator[tuple[Traversable, PurePosixPath]]:
    for child in node.iterdir():
        if child.is_dir():
            yield from _walk(child, prefix / child.name)
        else:
            yield child, prefix / _RENAMES.get(child.name, child.name)
