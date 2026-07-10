"""Tests for the manifest task runner."""

from pathlib import Path

import pytest

from init_configurator.manifest import Manifest, ManifestError
from init_configurator.runner import find_task, run_task


def build_manifest(stacks: list[dict[str, object]]) -> Manifest:
    return Manifest.model_validate(
        {"schema_version": 1, "project": {"name": "demo"}, "stacks": stacks}
    )


PY_STACK: dict[str, object] = {
    "name": "api",
    "language": "python",
    "version": "3.12",
    "package_manager": "uv",
    "dependency_files": ["pyproject.toml"],
    "tasks": {"test": "uv run pytest"},
}
NODE_STACK: dict[str, object] = {
    "name": "web",
    "language": "node",
    "version": "24",
    "package_manager": "pnpm",
    "dependency_files": ["package.json"],
    "tasks": {"test": "pnpm test"},
}


class TestFindTask:
    def test_unknown_task_lists_what_exists(self) -> None:
        with pytest.raises(ManifestError, match="available: api:test"):
            find_task(build_manifest([PY_STACK]), "deploy")

    def test_ambiguous_task_suggests_stack_flag(self) -> None:
        with pytest.raises(ManifestError, match="--stack"):
            find_task(build_manifest([PY_STACK, NODE_STACK]), "test")

    def test_stack_flag_disambiguates(self) -> None:
        stack = find_task(build_manifest([PY_STACK, NODE_STACK]), "test", stack_name="web")
        assert stack.name == "web"


class TestRunTask:
    def test_runs_from_stack_root_regardless_of_start_dir(self, tmp_path: Path) -> None:
        (tmp_path / "project.yaml").write_text(
            """\
schema_version: 1
project: {name: demo}
stacks:
  - name: api
    language: python
    version: "3.12"
    package_manager: uv
    dependency_files: [pyproject.toml]
    tasks:
      mark: python -c "import pathlib; pathlib.Path('marker.txt').write_text('ok')"
""",
            encoding="utf-8",
        )
        nested = tmp_path / "src" / "deep"
        nested.mkdir(parents=True)

        exit_code = run_task("mark", start=nested)

        assert exit_code == 0
        # The marker landed at the STACK root, not in the folder we started from.
        assert (tmp_path / "marker.txt").read_text(encoding="utf-8") == "ok"
        assert not (nested / "marker.txt").exists()
