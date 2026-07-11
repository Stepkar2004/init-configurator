"""The shipped genome and the repo's own skills are the same files, enforced.

This repo dogfoods what it ships: `.claude/skills/` is where sessions here read
the transferable skills, `src/init_configurator/genome/skills/` is what `initc
spawn` delivers. Two copies of markdown drift silently -- no import breaks, no
type error -- so equality is a gate. Edit a skill, mirror it into the genome
(or the other way), same commit.

`project-base` is exempt on purpose: the repo's copy is its own evolved
instance, and downstream copies are generated per project by `beacons.py`.
"""

from collections.abc import Iterator
from importlib.resources.abc import Traversable
from pathlib import Path

from init_configurator.spawn import genome_root

REPO_SKILLS = Path(__file__).resolve().parents[1] / ".claude" / "skills"
SHIPPED_SKILLS = ("bootstrap", "skill-manager", "workflow")


def _relative_files(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class TestGenomeMatchesRepoSkills:
    def test_every_shipped_skill_matches_the_repo_copy(self) -> None:
        for skill in SHIPPED_SKILLS:
            packaged_root = genome_root().joinpath("skills", skill)
            packaged = {
                str(rel): src.read_text(encoding="utf-8")
                for src, rel in _walk_packaged(packaged_root)
            }
            repo = _relative_files(REPO_SKILLS / skill)
            assert packaged == repo, (
                f"genome/skills/{skill} differs from .claude/skills/{skill} - "
                f"they are the same skill; edit both in the same commit"
            )

    def test_the_genome_ships_no_project_base(self) -> None:
        names = {entry.name for entry in genome_root().joinpath("skills").iterdir()}
        assert names == set(SHIPPED_SKILLS)


def _walk_packaged(node: Traversable, prefix: str = "") -> Iterator[tuple[Traversable, str]]:
    for child in node.iterdir():
        rel = f"{prefix}{child.name}"
        if child.is_dir():
            yield from _walk_packaged(child, f"{rel}/")
        else:
            yield child, rel
