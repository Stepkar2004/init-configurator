"""Local mode: materialize a manifest with everything inside the project folder.

``initc init`` (without ``--docker``) runs through four steps, in order:

1. scaffold — write starter files for every stack whose files are missing,
   plus context beacons and the declared data dirs. Existing files are NEVER
   overwritten: scaffolding is idempotent and safe to re-run.
2. contract — (re)generate ``.env.example`` from the manifest's env list.
3. install — create in-project environments (./.venv, ./node_modules) via the
   stack's package manager. No global installs, ever.
4. report — say exactly what was created, skipped, and run.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from init_configurator.beacons import PrimaryChoice, context_beacons
from init_configurator.env_contract import write_env_example
from init_configurator.manifest import Manifest, Stack
from init_configurator.presets import scaffold_files

GITKEEP = "# Keeps this declared-but-empty directory in git.\n"


class SetupError(Exception):
    """A setup step failed; the message says which one and what to do next."""


@dataclass(frozen=True)
class InstallStep:
    """One command local mode will run, resolved and ready to execute."""

    description: str
    argv: tuple[str, ...]
    cwd: Path


def initialize(
    manifest: Manifest,
    root: Path,
    *,
    skip_install: bool = False,
    agent: PrimaryChoice = "agents",
) -> list[str]:
    """Run local mode against ``root`` and return human-readable report lines."""
    files = plan_files(manifest, pnpm_version=_pnpm_version())
    # Beacons join the same never-overwrite plan; the primary/pointer choice is
    # an init-time decision, so they aren't part of pure plan_files().
    files.update(context_beacons(manifest, agent))
    report = _write_missing(root, files)

    env_example = write_env_example(manifest, root)
    if env_example is not None:
        report.append(f"wrote {env_example.name} from the manifest env contract")

    if skip_install:
        report.append("skipped installs (--skip-install)")
        return report

    for step in install_steps(manifest, root):
        report.append(f"running: {step.description}")
        _run(step)
    return report


def plan_files(manifest: Manifest, *, pnpm_version: str | None = None) -> dict[str, str]:
    """Everything scaffolding MAY create, keyed by root-relative path.

    Which of these actually get written is decided later against the real
    filesystem (missing files only). Beacons are handled separately because
    the primary/pointer choice happens at init time.
    """
    files: dict[str, str] = {}
    for stack in manifest.stacks:
        for relpath, content in scaffold_files(stack, manifest, pnpm_version=pnpm_version).items():
            prefix = "" if stack.root == "." else f"{stack.root.rstrip('/')}/"
            files[f"{prefix}{relpath}"] = content
    for directory in manifest.paths.values():
        files[f"{directory.rstrip('/')}/.gitkeep"] = GITKEEP
    return files


def _write_missing(root: Path, files: dict[str, str]) -> list[str]:
    """Write the planned files that don't exist yet; report both outcomes."""
    report: list[str] = []
    for relpath, content in files.items():
        target = root / relpath
        if target.exists():
            report.append(f"skipped {relpath} (exists)")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        report.append(f"created {relpath}")
    return report


def install_steps(manifest: Manifest, root: Path) -> list[InstallStep]:
    """Build the install commands for every stack — pure, so tests can inspect them."""
    steps: list[InstallStep] = []
    for stack in manifest.stacks:
        stack_root = root / stack.root
        if stack.language == "python":
            steps.extend(_python_steps(stack, stack_root))
        else:
            steps.append(
                InstallStep(
                    description=f"{stack.package_manager} install ({stack.name})",
                    argv=(stack.package_manager, "install"),
                    cwd=stack_root,
                )
            )
    return steps


def _python_steps(stack: Stack, stack_root: Path) -> list[InstallStep]:
    if stack.package_manager == "uv":
        return [
            InstallStep(description=f"uv sync ({stack.name})", argv=("uv", "sync"), cwd=stack_root)
        ]
    # pip flavor: an in-project venv, then install each declared dependency file.
    venv_python = (
        stack_root / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / "python"
    )
    steps = [
        InstallStep(
            description=f"create ./.venv ({stack.name})",
            argv=("python", "-m", "venv", ".venv"),
            cwd=stack_root,
        )
    ]
    for dependency_file in stack.dependency_files:
        install_args = (
            ("-e", ".") if dependency_file == "pyproject.toml" else ("-r", dependency_file)
        )
        steps.append(
            InstallStep(
                description=f"pip install from {dependency_file} ({stack.name})",
                argv=(str(venv_python), "-m", "pip", "install", *install_args),
                cwd=stack_root,
            )
        )
    return steps


def _run(step: InstallStep) -> None:
    """Execute one install step, translating failures into actionable errors."""
    binary = shutil.which(step.argv[0])
    if binary is None:
        raise SetupError(
            f"'{step.argv[0]}' not found on PATH — install it first "
            f"(needed for: {step.description})"
        )
    result = subprocess.run([binary, *step.argv[1:]], cwd=step.cwd)
    if result.returncode != 0:
        raise SetupError(
            f"{step.description} failed with exit code {result.returncode} — "
            f"see the output above for the package manager's own error"
        )


def _pnpm_version() -> str | None:
    """Detect the installed pnpm version so package.json can pin the real thing."""
    pnpm = shutil.which("pnpm")
    if pnpm is None:
        return None
    result = subprocess.run([pnpm, "--version"], capture_output=True, text=True)
    return result.stdout.strip() or None
