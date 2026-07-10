"""Tests for the ``initc`` command line: every command, happy path and error path.

The product IS a CLI, so this file exercises it the way a user does. The last
test is the one that matters most: it runs a real ``initc init`` (real
``uv sync``) against a fresh project and then a real ``initc doctor``. Without
it, a scaffolded ``pyproject.toml`` pointing at a README nobody wrote shipped
as a hard exit-1 on the tool's headline command.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
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


class TestInit:
    def test_scaffolds_without_installing(self, project: Path) -> None:
        result = runner.invoke(cli.app, ["init", "--skip-install"])
        assert result.exit_code == 0
        assert "OK: demo-app set up locally" in result.output
        assert (project / "pyproject.toml").is_file()
        assert (project / "README.md").is_file()
        assert (project / "src" / "demo_app" / "__init__.py").is_file()
        assert (project / "AGENTS.md").is_file()

    def test_docker_mode_generates_container_files(self, project: Path) -> None:
        result = runner.invoke(cli.app, ["init", "--docker"])
        assert result.exit_code == 0
        assert "docker setup generated" in result.output
        assert (project / "Dockerfile").is_file()
        assert (project / "compose.yaml").is_file()

    def test_unknown_agent_is_rejected(self, project: Path) -> None:
        result = runner.invoke(cli.app, ["init", "--agent", "copilot"])
        assert result.exit_code == 1
        assert "--agent must be" in result.output


class TestRun:
    def test_runs_a_declared_task(self, project: Path) -> None:
        assert runner.invoke(cli.app, ["run", "hello"]).exit_code == 0

    def test_unknown_task_lists_what_exists(self, project: Path) -> None:
        result = runner.invoke(cli.app, ["run", "deploy"])
        assert result.exit_code == 1
        assert "available: api:hello" in result.output


@pytest.mark.skipif(shutil.which("uv") is None, reason="the round-trip shells out to real uv")
def test_init_then_doctor_round_trip(project: Path) -> None:
    """The one test that installs for real: scaffold -> uv sync -> doctor, all green.

    ``initc init`` used to exit 1 here, because the pyproject it wrote declared
    a readme it never created and hatchling refused to build the project.
    """
    init_result = runner.invoke(cli.app, ["init"])
    assert init_result.exit_code == 0, init_result.output
    assert (project / ".venv").is_dir()

    doctor_result = runner.invoke(cli.app, ["doctor"])
    assert doctor_result.exit_code == 0, doctor_result.output
    assert "0 problems" in doctor_result.output


@pytest.mark.skipif(shutil.which("pip") is None, reason="the round-trip shells out to real pip")
def test_pip_flavor_installs_the_tools_it_declares(project: Path) -> None:
    """The pip path scaffolds ruff/mypy/pytest -- the venv must actually have them.

    ``pip install -e .`` does not install PEP 735 dependency-groups, so this
    project used to end up with a venv that could not run its own `test` task,
    while doctor called it healthy.
    """
    (project / "project.yaml").write_text(
        MANIFEST.replace("package_manager: uv", "package_manager: pip"), encoding="utf-8"
    )
    init_result = runner.invoke(cli.app, ["init"])
    assert init_result.exit_code == 0, init_result.output

    venv_python = project / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / "python"
    probe = "from importlib.metadata import version; print(version('pytest'), version('ruff'))"
    installed = subprocess.run(
        [str(venv_python), "-c", probe], capture_output=True, text=True, timeout=60
    )
    assert installed.returncode == 0, installed.stderr
