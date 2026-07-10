"""Tests for doctor: three-state checks, remediation messages, per-repo disables."""

from pathlib import Path
from typing import Any, ClassVar

import pytest

from init_configurator import doctor
from init_configurator.doctor import (
    CheckResult,
    Status,
    format_results,
    has_failures,
    parse_env_file,
    run_doctor,
)
from tests.conftest import ManifestFactory

Binaries = dict[str, str | None]


def results_by_name(results: list[CheckResult]) -> dict[str, CheckResult]:
    return {result.name: result for result in results}


@pytest.fixture
def fake_binaries(monkeypatch: pytest.MonkeyPatch) -> Binaries:
    """Control what 'installed binaries' doctor sees, no subprocesses involved."""
    versions: Binaries = {"uv": "0.11.12", "python": "3.12.5"}
    monkeypatch.setattr(doctor, "_binary_version", lambda binary: versions.get(binary))
    monkeypatch.setattr(
        doctor.shutil, "which", lambda binary: "found" if versions.get(binary) else None
    )
    return versions


class TestStackChecks:
    def test_everything_present_is_all_ok(
        self, tmp_path: Path, fake_binaries: Binaries, build_manifest: ManifestFactory
    ) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "pyvenv.cfg").write_text("version = 3.12\n", encoding="utf-8")
        results = run_doctor(build_manifest(), tmp_path)
        assert not has_failures(results)
        assert all(result.status is Status.OK for result in results)

    def test_missing_package_manager_fails_with_fix(
        self, tmp_path: Path, fake_binaries: Binaries, build_manifest: ManifestFactory
    ) -> None:
        fake_binaries["uv"] = None
        checks = results_by_name(run_doctor(build_manifest(), tmp_path))
        assert checks["binary:uv"].status is Status.FAIL
        assert checks["binary:uv"].fix is not None
        assert "astral" in checks["binary:uv"].fix

    def test_uv_stack_only_warns_on_runtime_mismatch(
        self, tmp_path: Path, fake_binaries: Binaries, build_manifest: ManifestFactory
    ) -> None:
        fake_binaries["python"] = "3.11.9"
        checks = results_by_name(run_doctor(build_manifest(), tmp_path))
        assert checks["runtime:api"].status is Status.WARN
        assert checks["runtime:api"].fix is not None
        assert "uv fetches python 3.12" in checks["runtime:api"].fix

    def test_pip_stack_fails_on_runtime_mismatch(
        self, tmp_path: Path, fake_binaries: Binaries, build_manifest: ManifestFactory
    ) -> None:
        fake_binaries.update({"python": "3.11.9", "pip": "24.0"})
        manifest = build_manifest()
        manifest.stacks[0].package_manager = "pip"
        checks = results_by_name(run_doctor(manifest, tmp_path))
        assert checks["runtime:api"].status is Status.FAIL

    def test_missing_dependency_file_fails(
        self, tmp_path: Path, fake_binaries: Binaries, build_manifest: ManifestFactory
    ) -> None:
        checks = results_by_name(run_doctor(build_manifest(), tmp_path))
        assert checks["deps:api:pyproject.toml"].status is Status.FAIL
        assert checks["deps:api:pyproject.toml"].fix is not None
        assert "initc init" in checks["deps:api:pyproject.toml"].fix

    def test_missing_venv_is_a_warning_not_failure(
        self, tmp_path: Path, fake_binaries: Binaries, build_manifest: ManifestFactory
    ) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        results = run_doctor(build_manifest(), tmp_path)
        checks = results_by_name(results)
        assert checks["install:api"].status is Status.WARN
        assert not has_failures(results)

    def test_a_half_installed_venv_is_not_reported_as_ready(
        self, tmp_path: Path, fake_binaries: Binaries, build_manifest: ManifestFactory
    ) -> None:
        # An empty .venv/ is what an interrupted install leaves behind. Doctor
        # used to call that healthy: the check asked only whether the directory
        # was there, which answers "did something run", not "can I work here".
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        (tmp_path / ".venv").mkdir()
        checks = results_by_name(run_doctor(build_manifest(), tmp_path))
        assert checks["install:api"].status is Status.WARN

        (tmp_path / ".venv" / "pyvenv.cfg").write_text("version = 3.12\n", encoding="utf-8")
        checks = results_by_name(run_doctor(build_manifest(), tmp_path))
        assert checks["install:api"].status is Status.OK


class TestRequiresAndDisable:
    def test_missing_required_binary_fails_with_reason(
        self, tmp_path: Path, fake_binaries: Binaries, build_manifest: ManifestFactory
    ) -> None:
        manifest = build_manifest(requires=[{"name": "ffmpeg", "reason": "audio preprocessing"}])
        checks = results_by_name(run_doctor(manifest, tmp_path))
        assert checks["requires:ffmpeg"].status is Status.FAIL
        assert "audio preprocessing" in checks["requires:ffmpeg"].message

    def test_disabled_checks_are_dropped(
        self, tmp_path: Path, fake_binaries: Binaries, build_manifest: ManifestFactory
    ) -> None:
        manifest = build_manifest(doctor={"disable": ["install:api"]})
        assert "install:api" not in results_by_name(run_doctor(manifest, tmp_path))


class TestEnvChecks:
    ENV: ClassVar[list[dict[str, Any]]] = [
        {"name": "DATABASE_URL", "required": True},
        {"name": "OPTIONAL_FLAG", "required": False},
    ]

    def test_required_var_satisfied_by_dotenv_file(
        self, tmp_path: Path, fake_binaries: Binaries, build_manifest: ManifestFactory
    ) -> None:
        (tmp_path / ".env").write_text("DATABASE_URL=postgres://x\n", encoding="utf-8")
        checks = results_by_name(run_doctor(build_manifest(env=self.ENV), tmp_path))
        assert checks["env:DATABASE_URL"].status is Status.OK

    def test_required_var_missing_fails_with_fix(
        self, tmp_path: Path, fake_binaries: Binaries, build_manifest: ManifestFactory
    ) -> None:
        checks = results_by_name(run_doctor(build_manifest(env=self.ENV), tmp_path))
        assert checks["env:DATABASE_URL"].status is Status.FAIL
        assert checks["env:DATABASE_URL"].fix is not None
        assert ".env" in checks["env:DATABASE_URL"].fix

    def test_optional_var_missing_is_silent(
        self, tmp_path: Path, fake_binaries: Binaries, build_manifest: ManifestFactory
    ) -> None:
        checks = results_by_name(run_doctor(build_manifest(env=self.ENV), tmp_path))
        assert "env:OPTIONAL_FLAG" not in checks

    def test_env_sync_warns_on_drift_both_ways(
        self, tmp_path: Path, fake_binaries: Binaries, build_manifest: ManifestFactory
    ) -> None:
        (tmp_path / ".env.example").write_text("STALE_VAR=\n", encoding="utf-8")
        checks = results_by_name(run_doctor(build_manifest(env=self.ENV), tmp_path))
        assert checks["env-sync"].status is Status.WARN
        assert "DATABASE_URL" in checks["env-sync"].message  # declared but not templated
        assert "STALE_VAR" in checks["env-sync"].message  # templated but not declared

    def test_env_sync_ok_when_in_sync(
        self, tmp_path: Path, fake_binaries: Binaries, build_manifest: ManifestFactory
    ) -> None:
        (tmp_path / ".env.example").write_text("DATABASE_URL=\nOPTIONAL_FLAG=\n", encoding="utf-8")
        checks = results_by_name(run_doctor(build_manifest(env=self.ENV), tmp_path))
        assert checks["env-sync"].status is Status.OK


class TestHelpers:
    def test_parse_env_file_skips_comments_and_junk(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# comment\n\nKEY=value\nSPACED = padded \nNOEQUALS\n", encoding="utf-8"
        )
        assert parse_env_file(env_file) == {"KEY": "value", "SPACED": "padded"}

    def test_parse_env_missing_file_is_empty(self, tmp_path: Path) -> None:
        assert parse_env_file(tmp_path / ".env") == {}

    def test_version_prefix_matching(self) -> None:
        assert doctor._version_matches("3.12", "3.12.5")
        assert doctor._version_matches("24", "24.1.0")
        assert not doctor._version_matches("3.12", "3.1.2")
        assert not doctor._version_matches("3.12.6", "3.12")

    def test_format_results_puts_fix_under_non_ok_lines(self) -> None:
        lines = format_results(
            [
                CheckResult("binary:uv", Status.OK, "uv 0.11.12", fix="never shown"),
                CheckResult("env:X", Status.FAIL, "not set", fix="copy .env.example"),
            ]
        )
        assert lines[0] == "  ok    binary:uv - uv 0.11.12"
        assert "never shown" not in "\n".join(lines)
        assert lines[2] == "        fix: copy .env.example"
        assert lines[-1] == "Doctor: 1 ok, 0 warnings, 1 problems"
