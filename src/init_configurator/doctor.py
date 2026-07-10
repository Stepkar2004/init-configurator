"""Doctor: verify the machine can run this project BEFORE setup fails midway.

Design borrowed from the best doctors in the business:

- three-state results — ``ok`` / ``warn`` / ``fail`` — so "will break" and
  "works but worth knowing" stay distinct (flutter doctor);
- every failure prints its fix next to the diagnosis (brew doctor);
- every check is named and can be disabled per repo via ``doctor.disable``
  in project.yaml (expo doctor);
- the warning bar stays HIGH: a doctor that over-warns trains people to
  ignore it, which is worse than no doctor at all.

The ``.env`` file is parsed, never sourced — config must not execute code.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from init_configurator.env_contract import ENV_EXAMPLE_FILENAME
from init_configurator.languages import provider_for
from init_configurator.manifest import Manifest, Stack

VERSION_RE = re.compile(r"(\d+(?:\.\d+)*)")


class Status(StrEnum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


@dataclass(frozen=True)
class CheckResult:
    """One named check's outcome; ``fix`` is the remediation when not ok."""

    name: str
    status: Status
    message: str
    fix: str | None = None


def run_doctor(manifest: Manifest, root: Path) -> list[CheckResult]:
    """Run every applicable check, minus the ones this repo disabled."""
    results: list[CheckResult] = []
    for stack in manifest.stacks:
        results.extend(_stack_checks(stack, root))
    results.extend(_requires_checks(manifest))
    results.extend(_env_checks(manifest, root))
    disabled = set(manifest.doctor.disable)
    return [result for result in results if result.name not in disabled]


def has_failures(results: list[CheckResult]) -> bool:
    return any(result.status is Status.FAIL for result in results)


def format_results(results: list[CheckResult]) -> list[str]:
    """Render the checklist plus a one-line summary, plain ASCII on purpose."""
    lines = []
    for result in results:
        lines.append(f"  {result.status.value:<5} {result.name} - {result.message}")
        if result.fix and result.status is not Status.OK:
            lines.append(f"        fix: {result.fix}")
    counts = {status: sum(1 for r in results if r.status is status) for status in Status}
    lines.append(
        f"Doctor: {counts[Status.OK]} ok, {counts[Status.WARN]} warnings, "
        f"{counts[Status.FAIL]} problems"
    )
    return lines


# --- stack checks -----------------------------------------------------------


def _stack_checks(stack: Stack, root: Path) -> list[CheckResult]:
    results = [_package_manager_check(stack), _runtime_check(stack)]
    results.extend(_dependency_file_checks(stack, root))
    results.append(_install_dir_check(stack, root))
    return results


def _package_manager_check(stack: Stack) -> CheckResult:
    name = f"binary:{stack.package_manager}"
    version = _binary_version(stack.package_manager)
    if version is None:
        return CheckResult(
            name,
            Status.FAIL,
            f"'{stack.package_manager}' not found on PATH (stack '{stack.name}' installs with it)",
            fix=provider_for(stack.language).package_manager_fix.get(stack.package_manager),
        )
    return CheckResult(name, Status.OK, f"{stack.package_manager} {version}")


def _runtime_check(stack: Stack) -> CheckResult:
    """Is the declared runtime available in a matching version?

    A uv stack only WARNS on a missing/mismatched interpreter — uv downloads
    the requested one itself during ``uv sync``. Everything else fails hard.
    """
    name = f"runtime:{stack.name}"
    binary = provider_for(stack.language).runtime_binary
    actual = _binary_version(binary)
    uv_managed = stack.package_manager == "uv"
    if actual is None:
        status = Status.WARN if uv_managed else Status.FAIL
        fix = (
            f"nothing to do - uv fetches python {stack.version} on sync"
            if uv_managed
            else f"install {stack.language} {stack.version}"
        )
        return CheckResult(name, status, f"'{binary}' not found on PATH", fix=fix)
    if not _version_matches(stack.version, actual):
        status = Status.WARN if uv_managed else Status.FAIL
        fix = (
            f"nothing to do - uv fetches python {stack.version} on sync"
            if uv_managed
            else f"install {stack.language} {stack.version} (found {actual})"
        )
        return CheckResult(
            name, status, f"{binary} {actual} does not match declared '{stack.version}'", fix=fix
        )
    return CheckResult(name, Status.OK, f"{binary} {actual} matches '{stack.version}'")


def _dependency_file_checks(stack: Stack, root: Path) -> list[CheckResult]:
    results = []
    for dependency_file in stack.dependency_files:
        path = root / stack.root / dependency_file
        name = f"deps:{stack.name}:{dependency_file}"
        if path.is_file():
            results.append(CheckResult(name, Status.OK, f"{dependency_file} present"))
        else:
            results.append(
                CheckResult(
                    name,
                    Status.FAIL,
                    f"declared dependency file {dependency_file} is missing",
                    fix="initc init  (scaffolds declared files that don't exist)",
                )
            )
    return results


def _install_dir_check(stack: Stack, root: Path) -> CheckResult:
    """Has local setup run yet? Missing env is a warn, not a failure."""
    directory = provider_for(stack.language).install_dir
    name = f"install:{stack.name}"
    if (root / stack.root / directory).is_dir():
        return CheckResult(name, Status.OK, f"./{directory} exists")
    return CheckResult(
        name,
        Status.WARN,
        f"./{directory} not created yet",
        fix="initc init",
    )


# --- requires / env checks --------------------------------------------------


def _requires_checks(manifest: Manifest) -> list[CheckResult]:
    results = []
    for requirement in manifest.requires:
        name = f"requires:{requirement.name}"
        if shutil.which(requirement.name):
            results.append(CheckResult(name, Status.OK, f"{requirement.name} present"))
        else:
            results.append(
                CheckResult(
                    name,
                    Status.FAIL,
                    f"'{requirement.name}' not found on PATH - needed for: {requirement.reason}",
                    fix=f"install {requirement.name}",
                )
            )
    return results


def _env_checks(manifest: Manifest, root: Path) -> list[CheckResult]:
    if not manifest.env:
        return []
    results = [_env_sync_check(manifest, root)]
    dotenv = parse_env_file(root / ".env")
    for var in manifest.env:
        if not var.required:
            continue  # optional vars never warn - the bar stays high
        name = f"env:{var.name}"
        if var.name in os.environ or var.name in dotenv:
            results.append(CheckResult(name, Status.OK, "set"))
        else:
            results.append(
                CheckResult(
                    name,
                    Status.FAIL,
                    f"required env var {var.name} is not set (checked shell env and .env)",
                    fix=f"copy {ENV_EXAMPLE_FILENAME} to .env and fill in {var.name}",
                )
            )
    return results


def _env_sync_check(manifest: Manifest, root: Path) -> CheckResult:
    """Diff manifest env names against .env.example keys, both directions."""
    example_path = root / ENV_EXAMPLE_FILENAME
    if not example_path.is_file():
        return CheckResult(
            "env-sync",
            Status.WARN,
            f"{ENV_EXAMPLE_FILENAME} missing while project.yaml declares env vars",
            fix="initc env",
        )
    declared = {var.name for var in manifest.env}
    templated = set(parse_env_file(example_path))
    missing = declared - templated
    extra = templated - declared
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing from example: {', '.join(sorted(missing))}")
        if extra:
            details.append(f"not in manifest: {', '.join(sorted(extra))}")
        return CheckResult(
            "env-sync",
            Status.WARN,
            f"{ENV_EXAMPLE_FILENAME} drifted from project.yaml ({'; '.join(details)})",
            fix="initc env  (regenerates the example; add new vars to project.yaml)",
        )
    return CheckResult("env-sync", Status.OK, f"{ENV_EXAMPLE_FILENAME} matches the manifest")


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE lines; comments and blanks skipped; nothing is executed."""
    if not path.is_file():
        return {}
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        entries[key.strip()] = value.strip()
    return entries


# --- version helpers ---------------------------------------------------------


def _binary_version(binary: str) -> str | None:
    """The version a binary reports, or ``None`` when it isn't usable."""
    resolved = shutil.which(binary)
    if resolved is None:
        return None
    try:
        output = subprocess.run(
            [resolved, "--version"], capture_output=True, text=True, timeout=15
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    found = VERSION_RE.search(output)
    return found.group(1) if found else None


def _version_matches(wanted: str, actual: str) -> bool:
    """Prefix match on version segments: wanted '3.12' accepts actual '3.12.5'."""
    wanted_parts = wanted.split(".")
    return actual.split(".")[: len(wanted_parts)] == wanted_parts
