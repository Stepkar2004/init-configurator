"""One runtime per supported language: how to CHECK a stack, never how to build one.

This module is the verification half of what used to be a full language
registry. The generation half (starter files, install steps, Dockerfiles) was
amputated on purpose: file contents rot in templates, so writing them belongs
to an agent guided by ``.claude/skills/bootstrap/`` and its per-stack
references. What a script CAN answer deterministically stays here -- which
binary proves the runtime exists, where dependencies must land, and what a
finished install actually looks like on disk. doctor is the only consumer.

Import direction is one-way: nothing here imports ``manifest``; a test asserts
this registry and the manifest's language tables agree, so a language cannot be
half-added. An unregistered language never reaches ``runtime_for`` -- a missing
entry is a bug in this file, not bad user input.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar, Protocol


class RuntimeCheck(Protocol):
    """Everything doctor needs to know about one language.

    The data members are read-only properties so implementations can declare
    them as plain class attributes.
    """

    @property
    def runtime_binary(self) -> str:
        """The binary whose ``--version`` reports the runtime (doctor checks it)."""
        ...

    @property
    def install_dir(self) -> str:
        """In-project dependency directory. No global installs; doctor names it."""
        ...

    @property
    def package_manager_fix(self) -> Mapping[str, str]:
        """How to obtain each package manager, keyed by its name.

        The keys must match ``manifest.PACKAGE_MANAGERS`` for this language --
        doctor prints one of these for any manager the manifest accepts, and a
        test enforces the two tables agree.
        """
        ...

    def install_ok(self, stack_root: Path) -> bool:
        """Did install actually produce a usable environment here?

        ``install_dir`` existing answers "did something run", not "did it
        finish" -- an interrupted install leaves the directory behind. Each
        runtime names an artifact its package manager writes last.
        """
        ...


class PythonRuntime:
    """uv or pip, dependencies in an in-project ``.venv``."""

    runtime_binary: ClassVar[str] = "python"
    install_dir: ClassVar[str] = ".venv"
    package_manager_fix: ClassVar[Mapping[str, str]] = {
        "uv": "install uv: https://docs.astral.sh/uv/getting-started/installation/",
        "pip": "install Python (pip ships with it): https://www.python.org/downloads/",
    }

    def install_ok(self, stack_root: Path) -> bool:
        # pyvenv.cfg, not the directory: `python -m venv` and `uv sync` both write
        # it, on every platform, and only once the interpreter is in place.
        return (stack_root / self.install_dir / "pyvenv.cfg").is_file()


class NodeRuntime:
    """pnpm or npm, dependencies in an in-project ``node_modules``."""

    runtime_binary: ClassVar[str] = "node"
    install_dir: ClassVar[str] = "node_modules"
    package_manager_fix: ClassVar[Mapping[str, str]] = {
        # Not `corepack enable`: Node >= 25 ships without corepack, and that
        # command exits 127 exactly where a fix message told someone to run it.
        "pnpm": "npm install -g pnpm  (Node >= 25 has no corepack)",
        "npm": "install Node.js (npm ships with it): https://nodejs.org/",
    }

    def install_ok(self, stack_root: Path) -> bool:
        # An empty node_modules/ is what a failed or interrupted install leaves.
        modules = stack_root / self.install_dir
        return modules.is_dir() and any(modules.iterdir())


#: The registry. Adding a language is adding one entry here (plus its Literal in
#: manifest.Language) and, for the HOW, a reference file under
#: .claude/skills/bootstrap/references/.
RUNTIMES: dict[str, RuntimeCheck] = {
    "python": PythonRuntime(),
    "node": NodeRuntime(),
}


def runtime_for(language: str) -> RuntimeCheck:
    """The runtime checks for a validated language.

    Raises:
        KeyError: only if ``manifest.Language`` accepts a language this module
            never registered -- a bug here, not a bad manifest.
    """
    try:
        return RUNTIMES[language]
    except KeyError as exc:
        raise KeyError(
            f"language '{language}' passed manifest validation but has no entry "
            f"in runtimes.RUNTIMES"
        ) from exc
