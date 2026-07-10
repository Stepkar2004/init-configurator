"""One provider per supported language: the single place a language is described.

Before this module, ``if stack.language == "python": ... else: ...`` appeared in
five files. Four of those ``else`` branches would have handed a Go stack *Node*
behavior, and the fifth raised a bare ``KeyError``. Adding a language meant
finding all five and getting all five right; forgetting one produced silently
wrong output rather than an error.

A provider records everything the rest of the tool needs to know about a
language -- which binary provides its runtime, where its dependencies land, how
to install them, what its starter files and Dockerfile look like. ``LANGUAGES``
is the only place a language is registered, so adding one is adding one object.

Import direction is one-way: this module imports ``manifest`` for the types it
works with, never the reverse. Validation happens in ``manifest``, so an
unregistered language never reaches ``provider_for`` -- which is why a missing
provider is a bug in this file, not bad user input.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Protocol

from init_configurator.manifest import Manifest, Stack
from init_configurator.presets import node_preset, python_preset

# Paths inside an image are fine by definition - only host paths break clones.
UV_COPY = "COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv"  # path-lint: ignore


@dataclass(frozen=True)
class InstallStep:
    """One command local mode will run, resolved and ready to execute."""

    description: str
    argv: tuple[str, ...]
    cwd: Path


class LanguageProvider(Protocol):
    """Everything init-configurator needs to know about one language.

    The three data members are read-only properties so that implementations can
    declare them as plain class attributes.
    """

    @property
    def runtime_binary(self) -> str:
        """The binary whose ``--version`` reports the runtime (doctor checks it)."""
        ...

    @property
    def install_dir(self) -> str:
        """In-project dependency directory: proof that install ran. No global installs."""
        ...

    @property
    def package_manager_fix(self) -> Mapping[str, str]:
        """How to obtain each package manager, keyed by its name.

        The keys must match ``manifest.PACKAGE_MANAGERS`` for this language --
        doctor prints one of these for any manager the manifest accepts, and a
        test enforces the two tables agree.
        """
        ...

    def preset_files(
        self, stack: Stack, manifest: Manifest, *, pnpm_version: str | None = None
    ) -> dict[str, str]:
        """Starter files for one stack, keyed by stack-relative path."""
        ...

    def install_steps(self, stack: Stack, stack_root: Path) -> list[InstallStep]:
        """The commands that create this stack's in-project environment."""
        ...

    def dockerfile_body(self, stack: Stack) -> str:
        """Everything in the Dockerfile above the CMD line."""
        ...


class PythonProvider:
    """uv or pip, a src/ layout, and an in-project ``.venv``."""

    runtime_binary: ClassVar[str] = "python"
    install_dir: ClassVar[str] = ".venv"
    package_manager_fix: ClassVar[Mapping[str, str]] = {
        "uv": "install uv: https://docs.astral.sh/uv/getting-started/installation/",
        "pip": "install Python (pip ships with it): https://www.python.org/downloads/",
    }

    def preset_files(
        self, stack: Stack, manifest: Manifest, *, pnpm_version: str | None = None
    ) -> dict[str, str]:
        return python_preset.files(stack, manifest)  # pnpm_version is Node's business

    def install_steps(self, stack: Stack, stack_root: Path) -> list[InstallStep]:
        if stack.package_manager == "uv":
            return [
                InstallStep(f"uv sync ({stack.name})", ("uv", "sync"), stack_root),
            ]
        # pip flavor: an in-project venv, then install each declared dependency file.
        venv_python = (
            stack_root / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / "python"
        )
        steps = [
            InstallStep(
                f"create ./.venv ({stack.name})", ("python", "-m", "venv", ".venv"), stack_root
            )
        ]
        for dependency_file in stack.dependency_files:
            install_args = (
                ("-e", ".") if dependency_file == "pyproject.toml" else ("-r", dependency_file)
            )
            steps.append(
                InstallStep(
                    f"pip install from {dependency_file} ({stack.name})",
                    (str(venv_python), "-m", "pip", "install", *install_args),
                    stack_root,
                )
            )
        return steps

    def dockerfile_body(self, stack: Stack) -> str:
        if stack.package_manager != "uv":
            return _python_pip_body(stack)
        return f"""\
FROM python:{stack.version}-slim
{UV_COPY}
WORKDIR /app

# Dependencies first, project second - keeps the dependency layer cached
# across source-only changes.
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project
COPY . .
RUN uv sync --no-dev
"""


class NodeProvider:
    """pnpm or npm, a strict TypeScript setup, and an in-project ``node_modules``."""

    runtime_binary: ClassVar[str] = "node"
    install_dir: ClassVar[str] = "node_modules"
    package_manager_fix: ClassVar[Mapping[str, str]] = {
        "pnpm": (
            "corepack enable  (Node >= 25 ships without corepack: npm install -g corepack first)"
        ),
        "npm": "install Node.js (npm ships with it): https://nodejs.org/",
    }

    def preset_files(
        self, stack: Stack, manifest: Manifest, *, pnpm_version: str | None = None
    ) -> dict[str, str]:
        return node_preset.files(stack, manifest, pnpm_version=pnpm_version)

    def install_steps(self, stack: Stack, stack_root: Path) -> list[InstallStep]:
        return [
            InstallStep(
                f"{stack.package_manager} install ({stack.name})",
                (stack.package_manager, "install"),
                stack_root,
            )
        ]

    def dockerfile_body(self, stack: Stack) -> str:
        corepack = "RUN corepack enable\n" if stack.package_manager == "pnpm" else ""
        lockfile = "pnpm-lock.yaml*" if stack.package_manager == "pnpm" else "package-lock.json*"
        return f"""\
FROM node:{stack.version}-slim
{corepack}WORKDIR /app

COPY package.json {lockfile} ./
RUN {stack.package_manager} install
COPY . .
"""


def _python_pip_body(stack: Stack) -> str:
    requirement_files = [f for f in stack.dependency_files if f != "pyproject.toml"]
    lines = [f"FROM python:{stack.version}-slim", "WORKDIR /app", ""]
    for requirement_file in requirement_files:
        lines.append(f"COPY {requirement_file} ./")
        lines.append(f"RUN pip install --no-cache-dir -r {requirement_file}")
    lines.append("COPY . .")
    if "pyproject.toml" in stack.dependency_files:
        lines.append("RUN pip install --no-cache-dir .")
    return "\n".join(lines) + "\n"


#: The registry. Adding a language is adding one entry here (and its Literal in
#: manifest.Language, which is what makes the language expressible at all).
LANGUAGES: dict[str, LanguageProvider] = {
    "python": PythonProvider(),
    "node": NodeProvider(),
}


def provider_for(language: str) -> LanguageProvider:
    """The provider for a validated language.

    Raises:
        KeyError: only if ``manifest.Language`` accepts a language this module
            never registered -- a bug here, not a bad manifest.
    """
    try:
        return LANGUAGES[language]
    except KeyError as exc:
        raise KeyError(
            f"language '{language}' passed manifest validation but has no provider "
            f"in languages.LANGUAGES"
        ) from exc
