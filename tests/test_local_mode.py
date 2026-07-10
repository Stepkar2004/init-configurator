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

    def test_node_build_emits_src_only_and_lint_skips_ignored_files(
        self, node_manifest: Manifest
    ) -> None:
        # `biome check .` used to fail on a freshly built project: tsc compiled
        # tests/ into dist/, and biome lints dist/ unless pointed at .gitignore.
        files = plan_files(node_manifest)
        build = json.loads(files["frontend/tsconfig.build.json"])
        assert build["include"] == ["src"]
        assert build["compilerOptions"]["rootDir"] == "src"
        assert json.loads(files["frontend/tsconfig.json"])["compilerOptions"]["noEmit"] is True
        biome = json.loads(files["frontend/biome.json"])
        assert biome["vcs"]["useIgnoreFile"] is True
        # json.dumps always expands; biome's default collapses short arrays back
        # onto one line and then fails the tsconfigs it just read.
        assert biome["json"]["formatter"]["expand"] == "always"
        scripts = json.loads(files["frontend/package.json"])["scripts"]
        assert scripts["build"] == "tsc -p tsconfig.build.json"
        assert scripts["typecheck"] == "tsc --noEmit"

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


class TestLineEndings:
    """Generated files are read by tools that expect LF, on every OS."""

    @pytest.mark.parametrize("manifest_name", ["python_manifest", "node_manifest"])
    def test_nothing_scaffolded_contains_a_carriage_return(
        self, tmp_path: Path, manifest_name: str, request: pytest.FixtureRequest
    ) -> None:
        # Path.write_text translates \n to os.linesep, so every file written on
        # Windows carried CRLF and a fresh Node scaffold failed its own
        # `biome check` -- whose formatter defaults to LF -- with 5 errors.
        initialize(request.getfixturevalue(manifest_name), tmp_path, skip_install=True)
        written = [path for path in tmp_path.rglob("*") if path.is_file()]
        assert written, "the scaffold wrote nothing, so this proves nothing"
        assert [path.name for path in written if b"\r" in path.read_bytes()] == []


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

    def test_pip_stack_installs_the_declared_dev_group(
        self, tmp_path: Path, python_manifest: Manifest
    ) -> None:
        # `pip install -e .` does not install PEP 735 dependency-groups, so the
        # ruff/mypy/pytest the preset declares never reached the venv and
        # `initc run test` died with "pytest: command not found".
        python_manifest.stacks[0].package_manager = "pip"
        (tmp_path / "pyproject.toml").write_text(
            '[dependency-groups]\ndev = ["pytest"]\n', encoding="utf-8"
        )
        argvs = [s.argv for s in install_steps(python_manifest, tmp_path)]
        assert argvs[-1][-2:] == ("--group", "dev")
        assert argvs[1][-2:] == ("--upgrade", "pip")  # --group needs pip >= 25.1

    def test_pip_stack_without_a_dev_group_is_left_alone(
        self, tmp_path: Path, python_manifest: Manifest
    ) -> None:
        # pip exits non-zero on a group that isn't declared: a hand-written
        # pyproject must not turn `initc init` into a failure.
        python_manifest.stacks[0].package_manager = "pip"
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
        argvs = [s.argv for s in install_steps(python_manifest, tmp_path)]
        assert not any("--group" in argv for argv in argvs)

    def test_node_stack_installs_with_declared_manager(
        self, tmp_path: Path, node_manifest: Manifest
    ) -> None:
        steps = install_steps(node_manifest, tmp_path)
        assert steps[0].argv == ("pnpm", "install")
        assert steps[0].cwd == tmp_path / "frontend/"
