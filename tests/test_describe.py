"""Tests for describe: deterministic detection, honest FILL_ME gaps, valid drafts.

The invariant that matters most: a draft written from a detectable repo must
pass ``load_manifest`` unchanged -- describe exists to START the manifest
conversation, and a draft the tool itself rejects would start it with an error.
"""

from pathlib import Path

import pytest

from init_configurator.describe import FILL_ME, DescribeError, detect_stacks, render_draft
from init_configurator.manifest import load_manifest

PYPROJECT = """\
[project]
name = "climbing-log"
requires-python = ">=3.12"
"""

PACKAGE_JSON = """\
{
  "name": "web-frontend",
  "engines": {"node": ">=24"},
  "scripts": {"test": "vitest run", "build": "tsc -p tsconfig.build.json"}
}
"""


def make_python_repo(root: Path) -> None:
    (root / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    (root / "uv.lock").write_text("# lock\n", encoding="utf-8")
    (root / "tests").mkdir()


class TestDetection:
    def test_python_repo_with_uv_lock(self, tmp_path: Path) -> None:
        make_python_repo(tmp_path)
        stack = detect_stacks(tmp_path)[0]
        assert stack.language == "python"
        assert stack.package_manager == "uv"
        assert stack.version == "3.12"  # from requires-python
        assert stack.dependency_files == ("pyproject.toml",)
        assert dict(stack.tasks) == {"install": "uv sync", "test": "uv run pytest"}

    def test_python_version_file_beats_requires_python(self, tmp_path: Path) -> None:
        make_python_repo(tmp_path)
        (tmp_path / ".python-version").write_text("3.13.2\n", encoding="utf-8")
        assert detect_stacks(tmp_path)[0].version == "3.13.2"

    def test_pip_repo_without_lockfile(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("requests\n", encoding="utf-8")
        stack = detect_stacks(tmp_path)[0]
        assert stack.package_manager == "pip"
        assert stack.version == FILL_ME  # nothing on disk declared one
        assert dict(stack.tasks) == {"install": "pip install -e ."}

    def test_node_repo_maps_scripts_to_tasks(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(PACKAGE_JSON, encoding="utf-8")
        (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: 9\n", encoding="utf-8")
        stack = detect_stacks(tmp_path)[0]
        assert stack.language == "node"
        assert stack.package_manager == "pnpm"
        assert stack.version == "24"  # from engines.node
        assert dict(stack.tasks) == {
            "install": "pnpm install",
            "test": "pnpm run test",
            "build": "pnpm run build",
        }

    def test_polyglot_repo_finds_stacks_one_level_down(self, tmp_path: Path) -> None:
        api = tmp_path / "api"
        api.mkdir()
        make_python_repo(api)
        web = tmp_path / "web"
        web.mkdir()
        (web / "package.json").write_text(PACKAGE_JSON, encoding="utf-8")
        stacks = {stack.name: stack for stack in detect_stacks(tmp_path)}
        assert stacks["api"].root == "api"
        assert stacks["web"].root == "web"
        assert stacks["web"].package_manager == "npm"  # no pnpm lockfile here

    def test_dependency_dirs_are_never_stacks(self, tmp_path: Path) -> None:
        make_python_repo(tmp_path)
        modules = tmp_path / "node_modules" / "leftpad"
        modules.mkdir(parents=True)
        (tmp_path / "node_modules" / "package.json").write_text("{}", encoding="utf-8")
        assert [stack.language for stack in detect_stacks(tmp_path)] == ["python"]

    def test_two_languages_in_one_folder_get_distinct_names(self, tmp_path: Path) -> None:
        app = tmp_path / "app"
        app.mkdir()
        make_python_repo(app)
        (app / "package.json").write_text(PACKAGE_JSON, encoding="utf-8")
        names = {stack.name for stack in detect_stacks(tmp_path)}
        # Both stacks would be named after the folder; the language suffix keeps
        # the draft loadable far enough for validate to explain the shared root.
        assert names == {"app-python", "app-node"}


class TestDraft:
    def test_draft_from_a_real_repo_passes_load_manifest(self, tmp_path: Path) -> None:
        make_python_repo(tmp_path)
        (tmp_path / "project.yaml").write_text(render_draft(tmp_path), encoding="utf-8")
        manifest = load_manifest(tmp_path)
        assert manifest.project.name == "climbing-log"
        assert manifest.stacks[0].tasks["install"] == "uv sync"

    def test_undetectable_version_is_marked_not_guessed(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("requests\n", encoding="utf-8")
        draft = render_draft(tmp_path)
        assert f'version: "{FILL_ME}"' in draft
        assert "TODO: confirm" in draft

    def test_empty_repo_refuses_with_what_it_looked_for(self, tmp_path: Path) -> None:
        with pytest.raises(DescribeError, match=r"pyproject\.toml"):
            render_draft(tmp_path)

    def test_broken_package_json_is_a_loud_error(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{not json", encoding="utf-8")
        with pytest.raises(DescribeError, match="not valid JSON"):
            render_draft(tmp_path)
