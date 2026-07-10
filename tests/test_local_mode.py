"""Tests for local mode: scaffolding plans, never-overwrite writes, install commands."""

import json
from pathlib import Path

from init_configurator.local_mode import initialize, install_steps, plan_files
from init_configurator.manifest import Manifest

PYTHON_MANIFEST = Manifest.model_validate(
    {
        "schema_version": 1,
        "project": {"name": "demo-app", "description": "A demo."},
        "stacks": [
            {
                "name": "api",
                "language": "python",
                "version": "3.12",
                "package_manager": "uv",
                "dependency_files": ["pyproject.toml"],
                "tasks": {"test": "uv run pytest"},
            }
        ],
        "env": [{"name": "API_URL", "example": "http://localhost:8000"}],
        "paths": {"data": "data/"},
    }
)

NODE_MANIFEST = Manifest.model_validate(
    {
        "schema_version": 1,
        "project": {"name": "demo-web"},
        "stacks": [
            {
                "name": "web",
                "language": "node",
                "version": "24",
                "root": "frontend/",
                "package_manager": "pnpm",
                "dependency_files": ["package.json"],
            }
        ],
    }
)


class TestPlanFiles:
    def test_python_plan_contains_src_layout_and_configs(self) -> None:
        files = plan_files(PYTHON_MANIFEST)
        assert "src/demo_app/__init__.py" in files
        assert "tests/test_smoke.py" in files
        assert 'name = "demo-app"' in files["pyproject.toml"]
        assert 'requires-python = ">=3.12"' in files["pyproject.toml"]
        assert files["data/.gitkeep"]

    def test_requirements_stub_written_when_declared(self) -> None:
        manifest = PYTHON_MANIFEST.model_copy(deep=True)
        manifest.stacks[0].dependency_files.append("requirements.txt")
        files = plan_files(manifest)
        assert "requirements.txt" in files

    def test_node_plan_lives_under_stack_root(self) -> None:
        files = plan_files(NODE_MANIFEST, pnpm_version="10.5.0")
        package = json.loads(files["frontend/package.json"])
        assert package["name"] == "demo-web"
        assert package["packageManager"] == "pnpm@10.5.0"
        assert package["engines"]["node"] == ">=24"
        assert "frontend/tsconfig.json" in files

    def test_no_package_manager_pin_without_detected_version(self) -> None:
        files = plan_files(NODE_MANIFEST, pnpm_version=None)
        package = json.loads(files["frontend/package.json"])
        assert "packageManager" not in package


class TestInitialize:
    def test_scaffolds_beacons_and_env_example(self, tmp_path: Path) -> None:
        report = initialize(PYTHON_MANIFEST, tmp_path, skip_install=True, agent="claude")
        assert (tmp_path / "src" / "demo_app" / "__init__.py").is_file()
        assert "single source of truth" in (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "CLAUDE.md" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "API_URL=http://localhost:8000" in (
            (tmp_path / ".env.example").read_text(encoding="utf-8")
        )
        assert any("skipped installs" in line for line in report)

    def test_agents_is_default_primary(self, tmp_path: Path) -> None:
        initialize(PYTHON_MANIFEST, tmp_path, skip_install=True)
        assert "single source of truth" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "AGENTS.md" in (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")

    def test_rerun_never_overwrites(self, tmp_path: Path) -> None:
        initialize(PYTHON_MANIFEST, tmp_path, skip_install=True)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("# hand-edited\n", encoding="utf-8")
        report = initialize(PYTHON_MANIFEST, tmp_path, skip_install=True)
        assert pyproject.read_text(encoding="utf-8") == "# hand-edited\n"
        assert any("skipped pyproject.toml" in line for line in report)


class TestInstallSteps:
    def test_uv_stack_syncs_in_stack_root(self, tmp_path: Path) -> None:
        steps = install_steps(PYTHON_MANIFEST, tmp_path)
        assert [s.argv for s in steps] == [("uv", "sync")]
        assert steps[0].cwd == tmp_path

    def test_pip_stack_creates_venv_then_installs_each_file(self, tmp_path: Path) -> None:
        manifest = PYTHON_MANIFEST.model_copy(deep=True)
        manifest.stacks[0].package_manager = "pip"
        manifest.stacks[0].dependency_files = ["pyproject.toml", "requirements.txt"]
        argvs = [s.argv for s in install_steps(manifest, tmp_path)]
        assert argvs[0] == ("python", "-m", "venv", ".venv")
        assert argvs[1][-2:] == ("-e", ".")
        assert argvs[2][-2:] == ("-r", "requirements.txt")
        assert ".venv" in argvs[1][0]  # pip runs from inside the project venv

    def test_node_stack_installs_with_declared_manager(self, tmp_path: Path) -> None:
        steps = install_steps(NODE_MANIFEST, tmp_path)
        assert steps[0].argv == ("pnpm", "install")
        assert steps[0].cwd == tmp_path / "frontend/"
