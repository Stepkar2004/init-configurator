"""Tests for local mode: scaffolding plans, never-overwrite writes, install commands."""

import json
from pathlib import Path

import pytest

from init_configurator.local_mode import initialize, install_steps, plan_files
from init_configurator.manifest import Manifest
from tests.conftest import ManifestFactory, StackFactory


@pytest.fixture
def python_manifest(build_manifest: ManifestFactory) -> Manifest:
    """The default python stack plus an env contract and a declared data dir."""
    return build_manifest(
        env=[{"name": "API_URL", "example": "http://localhost:8000"}],
        paths={"data": "data/"},
    )


@pytest.fixture
def node_manifest(build_manifest: ManifestFactory, node_stack: StackFactory) -> Manifest:
    return build_manifest(stacks=[node_stack()])


class TestPlanFiles:
    def test_python_plan_contains_src_layout_and_configs(self, python_manifest: Manifest) -> None:
        files = plan_files(python_manifest)
        assert "src/demo_app/__init__.py" in files
        assert "tests/test_smoke.py" in files
        assert 'name = "demo-app"' in files["pyproject.toml"]
        assert 'requires-python = ">=3.12"' in files["pyproject.toml"]
        assert files["data/.gitkeep"]

    def test_a_readme_lands_beside_every_pyproject(
        self, build_manifest: ManifestFactory, python_stack: StackFactory
    ) -> None:
        # hatchling refuses to build when `readme =` points at a missing file,
        # which made `initc init` exit 1 on every fresh python project. The
        # stack lives in a subfolder here on purpose: the repo-root README
        # would otherwise hide a preset that forgot to write its own.
        files = plan_files(build_manifest(stacks=[python_stack(root="api/")]))
        assert 'readme = "README.md"' in files["api/pyproject.toml"]
        assert files["api/README.md"].startswith("# demo-app - api")

    def test_requirements_stub_written_when_declared(self, python_manifest: Manifest) -> None:
        python_manifest.stacks[0].dependency_files.append("requirements.txt")
        files = plan_files(python_manifest)
        assert "requirements.txt" in files

    def test_node_plan_lives_under_stack_root(self, node_manifest: Manifest) -> None:
        files = plan_files(node_manifest, pnpm_version="10.5.0")
        package = json.loads(files["frontend/package.json"])
        assert package["name"] == "demo-app"
        assert package["packageManager"] == "pnpm@10.5.0"
        assert package["engines"]["node"] == ">=24"
        assert "frontend/tsconfig.json" in files

    def test_no_package_manager_pin_without_detected_version(self, node_manifest: Manifest) -> None:
        files = plan_files(node_manifest, pnpm_version=None)
        package = json.loads(files["frontend/package.json"])
        assert "packageManager" not in package


class TestRootFiles:
    def test_stack_at_root_keeps_its_own_gitignore(self, python_manifest: Manifest) -> None:
        files = plan_files(python_manifest)
        assert ".venv/" in files[".gitignore"]  # the python preset's, not the root default

    def test_repo_root_gets_gitignore_and_readme_when_no_stack_owns_it(
        self, node_manifest: Manifest
    ) -> None:
        # A polyglot repo's stacks all live in subfolders, so nothing else
        # ignores the root .env that compose loads.
        files = plan_files(node_manifest)
        assert ".env" in files[".gitignore"]
        assert "!.env.example" in files[".gitignore"]
        assert files["README.md"].startswith("# demo-app")
        assert files["frontend/README.md"].startswith("# demo-app - web")


class TestInitialize:
    def test_scaffolds_beacons_and_env_example(
        self, tmp_path: Path, python_manifest: Manifest
    ) -> None:
        report = initialize(python_manifest, tmp_path, skip_install=True, agent="claude")
        assert (tmp_path / "src" / "demo_app" / "__init__.py").is_file()
        assert "single source of truth" in (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "CLAUDE.md" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "API_URL=http://localhost:8000" in (
            (tmp_path / ".env.example").read_text(encoding="utf-8")
        )
        assert any("skipped installs" in line for line in report)

    def test_agents_is_default_primary(self, tmp_path: Path, python_manifest: Manifest) -> None:
        initialize(python_manifest, tmp_path, skip_install=True)
        assert "single source of truth" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "AGENTS.md" in (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")

    def test_rerun_never_overwrites(self, tmp_path: Path, python_manifest: Manifest) -> None:
        initialize(python_manifest, tmp_path, skip_install=True)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("# hand-edited\n", encoding="utf-8")
        report = initialize(python_manifest, tmp_path, skip_install=True)
        assert pyproject.read_text(encoding="utf-8") == "# hand-edited\n"
        assert any("skipped pyproject.toml" in line for line in report)


class TestInstallSteps:
    def test_uv_stack_syncs_in_stack_root(self, tmp_path: Path, python_manifest: Manifest) -> None:
        steps = install_steps(python_manifest, tmp_path)
        assert [s.argv for s in steps] == [("uv", "sync")]
        assert steps[0].cwd == tmp_path

    def test_pip_stack_creates_venv_then_installs_each_file(
        self, tmp_path: Path, python_manifest: Manifest
    ) -> None:
        python_manifest.stacks[0].package_manager = "pip"
        python_manifest.stacks[0].dependency_files = ["pyproject.toml", "requirements.txt"]
        argvs = [s.argv for s in install_steps(python_manifest, tmp_path)]
        assert argvs[0] == ("python", "-m", "venv", ".venv")
        assert argvs[1][-2:] == ("-e", ".")
        assert argvs[2][-2:] == ("-r", "requirements.txt")
        assert ".venv" in argvs[1][0]  # pip runs from inside the project venv

    def test_node_stack_installs_with_declared_manager(
        self, tmp_path: Path, node_manifest: Manifest
    ) -> None:
        steps = install_steps(node_manifest, tmp_path)
        assert steps[0].argv == ("pnpm", "install")
        assert steps[0].cwd == tmp_path / "frontend/"
