"""Tests for the ``initc`` command line: every command, happy path and error path.

The product IS a CLI, so this file exercises it the way a user does. The
round-trip test is the one that matters most: ``initc describe`` against a real
repo must draft a manifest that ``initc validate`` then accepts -- a tool whose
two commands disagree with each other teaches nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from init_configurator import cli
from init_configurator.doctor import CheckResult, Status

runner = CliRunner()

MANIFEST = """\
schema_version: 1
project:
  name: demo-app
  description: A demo.
stacks:
  - name: api
    language: python
    version: "3.12"
    package_manager: uv
    dependency_files: [pyproject.toml]
    tasks:
      hello: python -c "print('hello from a task')"
"""

ENV_SECTION = """\
env:
  - name: API_URL
    required: false
    example: http://localhost:8000
"""


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A tmp dir holding a valid project.yaml, and cwd moved into it.

    Every command locates its project by walking up from the cwd, so chdir is
    part of the fixture rather than a step each test repeats.
    """
    (tmp_path / "project.yaml").write_text(MANIFEST, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestValidate:
    def test_prints_what_the_manifest_declares(self, project: Path) -> None:
        result = runner.invoke(cli.app, ["validate", str(project)])
        assert result.exit_code == 0
        assert "OK: demo-app" in result.output
        assert "api (python 3.12)" in result.output

    def test_missing_manifest_exits_one(self, tmp_path: Path) -> None:
        result = runner.invoke(cli.app, ["validate", str(tmp_path)])
        assert result.exit_code == 1
        assert "manifest not found" in result.output

    def test_validation_error_teaches_the_fix(self, tmp_path: Path) -> None:
        (tmp_path / "project.yaml").write_text(
            MANIFEST.replace('version: "3.12"', "version: 3.12"), encoding="utf-8"
        )
        result = runner.invoke(cli.app, ["validate", str(tmp_path)])
        assert result.exit_code == 1
        assert "stacks[0].version" in result.output
        assert "quote it" in result.output


class TestSchema:
    def test_writes_the_json_schema(self, tmp_path: Path) -> None:
        out = tmp_path / "nested" / "project.schema.json"
        result = runner.invoke(cli.app, ["schema", "--out", str(out)])
        assert result.exit_code == 0
        schema = json.loads(out.read_text(encoding="utf-8"))
        assert "stacks" in schema["properties"]


class TestEnv:
    def test_generates_the_example_file(self, project: Path) -> None:
        (project / "project.yaml").write_text(MANIFEST + ENV_SECTION, encoding="utf-8")
        result = runner.invoke(cli.app, ["env"])
        assert result.exit_code == 0
        assert "API_URL=http://localhost:8000" in (project / ".env.example").read_text(
            encoding="utf-8"
        )

    def test_says_nothing_to_generate_without_declared_vars(self, project: Path) -> None:
        result = runner.invoke(cli.app, ["env"])
        assert result.exit_code == 0
        assert "no env vars declared" in result.output
        assert not (project / ".env.example").exists()


class TestLintPaths:
    def test_clean_tree_passes(self, project: Path) -> None:
        result = runner.invoke(cli.app, ["lint-paths"])
        assert result.exit_code == 0
        assert "OK: no absolute paths found" in result.output

    def test_absolute_path_fails_with_the_offending_line(self, project: Path) -> None:
        (project / "loader.py").write_text(
            'DATA = "/home/someone/data.csv"\n',  # path-lint: ignore
            encoding="utf-8",
        )
        result = runner.invoke(cli.app, ["lint-paths"])
        assert result.exit_code == 1
        assert "loader.py:1" in result.output
        assert "FAIL: 1 absolute path found" in result.output


class TestDoctor:
    def test_exit_zero_when_nothing_fails(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        healthy = CheckResult("binary:uv", Status.OK, "uv 1.0")
        monkeypatch.setattr(cli, "run_doctor", lambda manifest, root: [healthy])
        result = runner.invoke(cli.app, ["doctor"])
        assert result.exit_code == 0
        assert "ok    binary:uv - uv 1.0" in result.output

    def test_exit_one_and_print_the_fix_when_a_check_fails(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        failure = CheckResult("binary:uv", Status.FAIL, "not found", fix="install uv")
        monkeypatch.setattr(cli, "run_doctor", lambda manifest, root: [failure])
        result = runner.invoke(cli.app, ["doctor"])
        assert result.exit_code == 1
        assert "fix: install uv" in result.output


class TestDescribe:
    def test_never_overwrites_an_existing_manifest(self, project: Path) -> None:
        result = runner.invoke(cli.app, ["describe", str(project)])
        assert result.exit_code == 1
        assert "already exists" in result.output
        # The manifest kept its original content.
        assert "demo-app" in (project / "project.yaml").read_text(encoding="utf-8")

    def test_undescribable_repo_says_what_it_looked_for(self, tmp_path: Path) -> None:
        result = runner.invoke(cli.app, ["describe", str(tmp_path)])
        assert result.exit_code == 1
        assert "pyproject.toml" in result.output


class TestRun:
    def test_runs_a_declared_task(self, project: Path) -> None:
        assert runner.invoke(cli.app, ["run", "hello"]).exit_code == 0

    def test_unknown_task_lists_what_exists(self, project: Path) -> None:
        result = runner.invoke(cli.app, ["run", "deploy"])
        assert result.exit_code == 1
        assert "available: api:hello" in result.output


def test_describe_then_validate_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The tool must accept its own draft: describe -> validate, both green."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "found-repo"\nrequires-python = ">=3.12"\n', encoding="utf-8"
    )
    (tmp_path / "uv.lock").write_text("# lock\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    monkeypatch.chdir(tmp_path)

    described = runner.invoke(cli.app, ["describe"])
    assert described.exit_code == 0, described.output
    assert (tmp_path / "project.yaml").is_file()

    validated = runner.invoke(cli.app, ["validate"])
    assert validated.exit_code == 0, validated.output
    assert "OK: found-repo" in validated.output
