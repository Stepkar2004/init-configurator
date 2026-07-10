"""Tests for docker mode: generated Dockerfiles, compose wiring, never-overwrite."""

from pathlib import Path

import yaml

from init_configurator.docker_mode import docker_files, initialize
from init_configurator.manifest import Manifest


def build_manifest(**overrides: object) -> Manifest:
    base: dict[str, object] = {
        "schema_version": 1,
        "project": {"name": "demo"},
        "stacks": [
            {
                "name": "api",
                "language": "python",
                "version": "3.12",
                "package_manager": "uv",
                "dependency_files": ["pyproject.toml"],
                "tasks": {"start": "uv run python -m demo"},
            }
        ],
    }
    base.update(overrides)
    return Manifest.model_validate(base)


class TestDockerfiles:
    def test_python_uv_dockerfile(self) -> None:
        dockerfile = docker_files(build_manifest())["Dockerfile"]
        assert "FROM python:3.12-slim" in dockerfile
        assert "ghcr.io/astral-sh/uv" in dockerfile
        assert "uv sync --no-dev --no-install-project" in dockerfile  # cached deps layer
        assert 'CMD ["sh", "-c", "uv run python -m demo"]' in dockerfile

    def test_python_pip_dockerfile_installs_each_requirements_file(self) -> None:
        manifest = build_manifest()
        manifest.stacks[0].package_manager = "pip"
        manifest.stacks[0].dependency_files = ["requirements.txt", "pyproject.toml"]
        dockerfile = docker_files(manifest)["Dockerfile"]
        assert "RUN pip install --no-cache-dir -r requirements.txt" in dockerfile
        assert "RUN pip install --no-cache-dir ." in dockerfile

    def test_node_pnpm_dockerfile_enables_corepack(self) -> None:
        manifest = build_manifest(
            stacks=[
                {
                    "name": "web",
                    "language": "node",
                    "version": "24",
                    "root": "frontend/",
                    "package_manager": "pnpm",
                    "dependency_files": ["package.json"],
                }
            ]
        )
        files = docker_files(manifest)
        dockerfile = files["frontend/Dockerfile"]
        assert "FROM node:24-slim" in dockerfile
        assert "RUN corepack enable" in dockerfile
        assert "pnpm-lock.yaml*" in dockerfile

    def test_missing_start_task_leaves_a_pointer_not_a_cmd(self) -> None:
        manifest = build_manifest()
        manifest.stacks[0].tasks = {}
        dockerfile = docker_files(manifest)["Dockerfile"]
        assert "\nCMD [" not in dockerfile
        assert "No 'start' or 'dev' task" in dockerfile


class TestCompose:
    def test_stacks_and_sidecars_become_services(self) -> None:
        manifest = build_manifest(
            env=[{"name": "DATABASE_URL"}],
            docker={"services": ["postgres:16"]},
        )
        compose = yaml.safe_load(docker_files(manifest)["compose.yaml"])
        assert compose["services"]["api"]["build"]["context"] == "."
        assert compose["services"]["api"]["env_file"] == [".env"]
        assert compose["services"]["postgres"] == {"image": "postgres:16"}

    def test_no_env_file_entry_without_declared_env(self) -> None:
        compose = yaml.safe_load(docker_files(build_manifest())["compose.yaml"])
        assert "env_file" not in compose["services"]["api"]

    def test_compose_false_skips_the_file(self) -> None:
        manifest = build_manifest(docker={"compose": False})
        assert "compose.yaml" not in docker_files(manifest)


class TestInitialize:
    def test_scaffolds_skill_beacons_and_docker_files(self, tmp_path: Path) -> None:
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

    def test_hand_edited_dockerfile_survives_rerun(self, tmp_path: Path) -> None:
        initialize(build_manifest(), tmp_path)
        (tmp_path / "Dockerfile").write_text("# mine now\n", encoding="utf-8")
        report = initialize(build_manifest(), tmp_path)
        assert (tmp_path / "Dockerfile").read_text(encoding="utf-8") == "# mine now\n"
        assert any("skipped Dockerfile" in line for line in report)
