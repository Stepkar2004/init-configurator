"""Tests for spawn: the genome lands additively; --force updates only skills.

The one behavior that matters most is the negative one: a file the target
already has must come through byte-identical. Spawn being additive-by-default is
what lets the bootstrap skill offer it on ANY repo without an interview about
overwriting -- the tool cannot destroy, so the only question left is whether
the user wants the genome at all. ``--force`` is the deliberate exception: it
lets the base's skills win, but never touches docs/standards and never deletes.
"""

from pathlib import Path

from typer.testing import CliRunner

from init_configurator.cli import app
from init_configurator.spawn import genome_root, spawn_genome

runner = CliRunner()

EXPECTED_LANDMARKS = [
    ".claude/skills/workflow/SKILL.md",
    ".claude/skills/skill-manager/references/evolve.md",
    ".claude/skills/bootstrap/references/python.md",
    ".gitattributes",
    ".gitignore",
    "docs/vision.md",
    "docs/state/log.md",
    "docs/posts/README.md",
]


class TestSpawnGenome:
    def test_fresh_target_receives_the_whole_genome(self, tmp_path: Path) -> None:
        target = tmp_path / "child"
        results = spawn_genome(target)
        assert results and all(spawned.outcome == "added" for spawned in results)
        for landmark in EXPECTED_LANDMARKS:
            assert (target / landmark).is_file(), f"missing {landmark}"

    def test_dotfiles_arrive_under_their_real_names(self, tmp_path: Path) -> None:
        spawn_genome(tmp_path)
        assert "eol=lf" in (tmp_path / ".gitattributes").read_text(encoding="utf-8")
        assert not (tmp_path / "_gitattributes").exists()  # the rename is total

    def test_spawn_is_idempotent(self, tmp_path: Path) -> None:
        spawn_genome(tmp_path)
        second = spawn_genome(tmp_path)
        assert second and all(spawned.outcome == "kept" for spawned in second)

    def test_existing_files_are_kept_byte_identical(self, tmp_path: Path) -> None:
        mine = "# my own ignore rules\nnode_modules/\n"
        (tmp_path / ".gitignore").write_text(mine, encoding="utf-8")
        results = spawn_genome(tmp_path)
        assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == mine
        gitignore = next(r for r in results if str(r.target) == ".gitignore")
        assert gitignore.outcome == "kept"

    def test_written_files_are_lf_on_every_os(self, tmp_path: Path) -> None:
        spawn_genome(tmp_path)
        raw = (tmp_path / ".claude/skills/workflow/SKILL.md").read_bytes()
        assert b"\r" not in raw

    def test_genome_never_carries_manifest_or_project_base(self, tmp_path: Path) -> None:
        """describe/bootstrap write these fresh per project; spawn must not."""
        spawn_genome(tmp_path)
        assert not (tmp_path / "project.yaml").exists()
        assert not (tmp_path / ".claude/skills/project-base").exists()


class TestForceSkills:
    WORKFLOW = ".claude/skills/workflow/SKILL.md"

    def test_force_replaces_a_diverged_skill_with_the_base_version(self, tmp_path: Path) -> None:
        spawn_genome(tmp_path)
        skill = tmp_path / self.WORKFLOW
        skill.write_text("# my own take on the workflow\n", encoding="utf-8")
        results = spawn_genome(tmp_path, force_skills=True)
        entry = next(r for r in results if str(r.target) == self.WORKFLOW)
        assert entry.outcome == "replaced"
        packaged = genome_root().joinpath("skills/workflow/SKILL.md").read_text(encoding="utf-8")
        assert skill.read_text(encoding="utf-8") == packaged

    def test_force_leaves_an_unchanged_skill_as_kept(self, tmp_path: Path) -> None:
        spawn_genome(tmp_path)
        results = spawn_genome(tmp_path, force_skills=True)
        assert all(r.outcome == "kept" for r in results)  # nothing diverged, nothing to replace

    def test_force_never_touches_docs_or_standards(self, tmp_path: Path) -> None:
        spawn_genome(tmp_path)
        (tmp_path / "docs/vision.md").write_text("MY REAL VISION\n", encoding="utf-8")
        (tmp_path / ".gitignore").write_text("my-own-rules/\n", encoding="utf-8")
        spawn_genome(tmp_path, force_skills=True)
        assert (tmp_path / "docs/vision.md").read_text(encoding="utf-8") == "MY REAL VISION\n"
        assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == "my-own-rules/\n"

    def test_force_never_deletes_a_skill_the_base_does_not_ship(self, tmp_path: Path) -> None:
        spawn_genome(tmp_path)
        mine = tmp_path / ".claude/skills/project-base/SKILL.md"
        mine.parent.mkdir(parents=True, exist_ok=True)
        mine.write_text("this repo's own constitution\n", encoding="utf-8")
        spawn_genome(tmp_path, force_skills=True)
        assert mine.read_text(encoding="utf-8") == "this repo's own constitution\n"


class TestSpawnCommand:
    def test_spawn_reports_added_and_next_step(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["spawn", str(tmp_path / "child")])
        assert result.exit_code == 0
        assert "added" in result.output
        assert "bootstrap" in result.output  # the discovery chain's next link
        assert "project-base is bootstrap-managed" in result.output  # the name-collision footgun
        assert result.output.isascii()

    def test_spawn_reports_kept_without_failing(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("mine\n", encoding="utf-8")
        result = runner.invoke(app, ["spawn", str(tmp_path)])
        assert result.exit_code == 0
        assert "kept" in result.output
        assert "not touched" in result.output

    def test_spawn_onto_a_file_teaches(self, tmp_path: Path) -> None:
        file_target = tmp_path / "a-file"
        file_target.write_text("hi", encoding="utf-8")
        result = runner.invoke(app, ["spawn", str(file_target)])
        assert result.exit_code == 1
        assert "folder" in result.output

    def test_spawn_force_reports_replaced(self, tmp_path: Path) -> None:
        runner.invoke(app, ["spawn", str(tmp_path)])
        (tmp_path / ".claude/skills/workflow/SKILL.md").write_text("mine\n", encoding="utf-8")
        result = runner.invoke(app, ["spawn", str(tmp_path), "--force"])
        assert result.exit_code == 0
        assert "replaced" in result.output
        assert result.output.isascii()
