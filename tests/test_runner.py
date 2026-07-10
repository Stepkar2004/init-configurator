"""Tests for the manifest task runner."""

from pathlib import Path

import pytest

from init_configurator.manifest import ManifestError
from init_configurator.runner import find_task, run_task
from tests.conftest import ManifestFactory, StackFactory


class TestFindTask:
    def test_unknown_task_lists_what_exists(self, build_manifest: ManifestFactory) -> None:
        with pytest.raises(ManifestError, match="available: api:start, api:test"):
            find_task(build_manifest(), "deploy")

    def test_ambiguous_task_suggests_stack_flag(
        self, build_manifest: ManifestFactory, python_stack: StackFactory, node_stack: StackFactory
    ) -> None:
        manifest = build_manifest(stacks=[python_stack(), node_stack()])
        with pytest.raises(ManifestError, match="--stack"):
            find_task(manifest, "test")

    def test_stack_flag_disambiguates(
        self, build_manifest: ManifestFactory, python_stack: StackFactory, node_stack: StackFactory
    ) -> None:
        manifest = build_manifest(stacks=[python_stack(), node_stack()])
        assert find_task(manifest, "test", stack_name="web").name == "web"


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
