"""Copy the packaged genome into a target project, additively.

Spawn is the mechanical half of inheritance; the judgment half stays with the
agent running the absorb skill's spawn procedure (review what was kept, record
lineage, run bootstrap next). This module only ever ADDS files: a target file
that already exists is reported as kept and never touched, so there is nothing
to interview about at this layer -- the tool cannot destroy, and the agent
decides whether merging genome content into kept files is wanted.

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

from init_configurator.textfile import write_text_lf

#: genome top-level folder -> where its contents land, relative to the target
_DESTINATIONS = {
    "skills": PurePosixPath(".claude/skills"),
    "standards": PurePosixPath(),
    "docs": PurePosixPath("docs"),
}

#: names that cannot exist verbatim inside the package (see module docstring)
_RENAMES = {"_gitignore": ".gitignore", "_gitattributes": ".gitattributes"}


class SpawnError(Exception):
    """Spawn cannot proceed; the message says why and what to do instead."""


@dataclass(frozen=True)
class SpawnedFile:
    """One genome file's fate in the target: created, or kept as it was."""

    target: PurePosixPath
    created: bool


def genome_root() -> Traversable:
    """The packaged genome directory (works installed and editable alike)."""
    return files("init_configurator").joinpath("genome")


def spawn_genome(target_dir: Path) -> list[SpawnedFile]:
    """Copy every genome file that is missing from ``target_dir``; skip the rest."""
    if target_dir.exists() and not target_dir.is_dir():
        raise SpawnError(
            f"{target_dir} is a file - spawn needs a project folder "
            f"(an existing one, or a path to create)"
        )
    results: list[SpawnedFile] = []
    for source, relative in sorted(_genome_files(), key=lambda pair: str(pair[1])):
        destination = target_dir / relative
        if destination.exists():
            results.append(SpawnedFile(relative, created=False))
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        write_text_lf(destination, source.read_text(encoding="utf-8"))
        results.append(SpawnedFile(relative, created=True))
    return results


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
