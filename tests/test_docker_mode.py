"""Tests for docker mode: generated Dockerfiles, compose wiring, never-overwrite."""

from pathlib import Path

import yaml

from init_configurator.docker_mode import docker_files, initialize
from tests.conftest import ManifestFactory, StackFactory


class TestDockerfiles:
    def test_python_uv_dockerfile(self, build_manifest: ManifestFactory) -> None:
        dockerfile = docker_files(build_manifest())["Dockerfile"]
        assert "FROM python:3.12-slim" in dockerfile
        assert "ghcr.io/astral-sh/uv" in dockerfile
        assert "uv sync --no-dev --no-install-project" in dockerfile  # cached deps layer
        assert 'CMD ["sh", "-c", "uv run python -m demo"]' in dockerfile

    def test_python_pip_dockerfile_installs_each_requirements_file(
        self, build_manifest: ManifestFactory
    ) -> None:
        manifest = build_manifest()
        manifest.stacks[0].package_manager = "pip"
        manifest.stacks[0].dependency_files = ["requirements.txt", "pyproject.toml"]
        dockerfile = docker_files(manifest)["Dockerfile"]
        assert "RUN pip install --no-cache-dir -r requirements.txt" in dockerfile
        assert "RUN pip install --no-cache-dir ." in dockerfile

    def test_node_pnpm_dockerfile_enables_corepack(
        self, build_manifest: ManifestFactory, node_stack: StackFactory
    ) -> None:
        files = docker_files(build_manifest(stacks=[node_stack()]))
        dockerfile = files["frontend/Dockerfile"]
        assert "FROM node:24-slim" in dockerfile
        assert "RUN corepack enable" in dockerfile
        assert "pnpm-lock.yaml*" in dockerfile

    def test_missing_start_task_leaves_a_pointer_not_a_cmd(
        self, build_manifest: ManifestFactory
    ) -> None:
        manifest = build_manifest()
        manifest.stacks[0].tasks = {}
        dockerfile = docker_files(manifest)["Dockerfile"]
        assert "\nCMD [" not in dockerfile
        assert "No 'start' or 'dev' task" in dockerfile


class TestDockerignore:
    def test_one_per_build_context(
        self, build_manifest: ManifestFactory, python_stack: StackFactory, node_stack: StackFactory
    ) -> None:
        # Docker reads .dockerignore only from the build context root, and each
        # stack root is its own context - a single root copy ignored nothing.
        files = docker_files(build_manifest(stacks=[python_stack(root="api/"), node_stack()]))
        assert ".dockerignore" not in files
        assert "node_modules" in files["api/.dockerignore"]
        assert "node_modules" in files["frontend/.dockerignore"]

    def test_stack_at_the_root_puts_it_at_the_root(self, build_manifest: ManifestFactory) -> None:
        assert ".dockerignore" in docker_files(build_manifest())


class TestCompose:
    def test_stacks_and_sidecars_become_services(self, build_manifest: ManifestFactory) -> None:
        manifest = build_manifest(
            env=[{"name": "DATABASE_URL"}],
            docker={"services": ["redis:7"]},
        )
        compose = yaml.safe_load(docker_files(manifest)["compose.yaml"])
        assert compose["services"]["api"]["build"]["context"] == "."
        assert compose["services"]["api"]["env_file"] == [".env"]
        assert compose["services"]["redis"] == {"image": "redis:7"}

    def test_stacks_wait_for_their_sidecars(self, build_manifest: ManifestFactory) -> None:
        manifest = build_manifest(docker={"services": ["redis:7", "postgres:16"]})
        compose = yaml.safe_load(docker_files(manifest)["compose.yaml"])
        assert compose["services"]["api"]["depends_on"] == ["postgres", "redis"]

    def test_postgres_gets_what_it_needs_to_start_and_persist(
        self, build_manifest: ManifestFactory
    ) -> None:
        # The official image refuses to boot without a password, and without a
        # volume the database dies with the container.
        manifest = build_manifest(docker={"services": ["postgres:16"]})
        compose = yaml.safe_load(docker_files(manifest)["compose.yaml"])
        postgres = compose["services"]["postgres"]
        assert postgres["environment"]["POSTGRES_PASSWORD"] == "${POSTGRES_PASSWORD:-postgres}"
        assert postgres["volumes"] == ["pgdata:/var/lib/postgresql/data"]  # path-lint: ignore
        assert "pgdata" in compose["volumes"]

    def test_no_depends_on_or_volumes_without_sidecars(
        self, build_manifest: ManifestFactory
    ) -> None:
        compose = yaml.safe_load(docker_files(build_manifest())["compose.yaml"])
        assert "depends_on" not in compose["services"]["api"]
        assert "volumes" not in compose

    def test_header_says_what_compose_cannot_guess(self, build_manifest: ManifestFactory) -> None:
        compose = docker_files(build_manifest())["compose.yaml"]
        assert "Ports are yours to choose" in compose
        assert "bind 0.0.0.0" in compose

    def test_no_env_file_entry_without_declared_env(self, build_manifest: ManifestFactory) -> None:
        compose = yaml.safe_load(docker_files(build_manifest())["compose.yaml"])
        assert "env_file" not in compose["services"]["api"]

    def test_compose_false_skips_the_file(self, build_manifest: ManifestFactory) -> None:
        manifest = build_manifest(docker={"compose": False})
        assert "compose.yaml" not in docker_files(manifest)


class TestInitialize:
    def test_scaffolds_skill_beacons_and_docker_files(
        self, tmp_path: Path, build_manifest: ManifestFactory
    ) -> None:
        initialize(build_manifest(), tmp_path, agent="claude")
        assert (tmp_path / "Dockerfile").is_file()
        assert (tmp_path / "compose.yaml").is_file()
        assert (tmp_path / ".dockerignore").is_file()
        skill = tmp_path / ".claude" / "skills" / "project-base" / "SKILL.md"
        assert "initc doctor" in skill.read_text(encoding="utf-8")
        # The discovery chain: primary beacon points at the skill.
        assert ".claude/skills/project-base/SKILL.md" in (tmp_path / "CLAUDE.md").read_text(
            encoding="utf-8"
        )

    def test_hand_edited_dockerfile_survives_rerun(
        self, tmp_path: Path, build_manifest: ManifestFactory
    ) -> None:
        initialize(build_manifest(), tmp_path)
        (tmp_path / "Dockerfile").write_text("# mine now\n", encoding="utf-8")
        report = initialize(build_manifest(), tmp_path)
        assert (tmp_path / "Dockerfile").read_text(encoding="utf-8") == "# mine now\n"
        assert any("skipped Dockerfile" in line for line in report)
