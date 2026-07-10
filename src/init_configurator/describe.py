"""Draft a ``project.yaml`` for an existing repo -- the first half of conjugation.

The old design assumed the folder was empty; this module is what "adapts to any
project" actually means. It inspects a working tree with deterministic rules
only -- which dependency files exist, which lockfile is present, what the config
files already say -- and writes a DRAFT manifest describing what it found.

Everything it cannot detect is marked ``FILL_ME`` with a TODO comment, never
guessed: a wrong guess in a manifest becomes a confident lie that doctor then
enforces. The draft is a starting point for a human (or an agent running the
bootstrap skill) to review, not a finished contract.
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any

from init_configurator.manifest import MANIFEST_FILENAME

FILL_ME = "FILL_ME"

# Folders that are never a stack root: tool output, caches, dependency dirs.
SKIP_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }
)

VERSION_RE = re.compile(r"(\d+(?:\.\d+)*)")


class DescribeError(Exception):
    """The repo could not be described; the message says what was looked for."""


@dataclass(frozen=True)
class DetectedStack:
    """One stack the inspection found, plus how sure it is about the version."""

    name: str
    language: str
    version: str  # FILL_ME when nothing on disk declared it
    root: str
    package_manager: str
    dependency_files: tuple[str, ...]
    tasks: tuple[tuple[str, str], ...]


def render_draft(root: Path) -> str:
    """The draft manifest text for ``root``.

    Raises:
        DescribeError: when no recognizable stack exists, or a dependency file
            is too broken to read.
    """
    stacks = detect_stacks(root)
    if not stacks:
        raise DescribeError(
            f"nothing to describe in {root}: no pyproject.toml, requirements.txt, "
            f"or package.json found there or one folder down"
        )
    lines = [
        f"# {MANIFEST_FILENAME} - drafted by `initc describe` on {date.today().isoformat()}.",
        "# This is what deterministic inspection could detect - review every line,",
        f"# replace any {FILL_ME}, then run `initc validate` and `initc doctor`.",
        "schema_version: 1",
        "",
        "project:",
        f"  name: {_yaml_str(_project_name(root))}",
        f"  description: {_yaml_str('FILL_ME: one line on what this project does.')}",
        "",
        "stacks:",
    ]
    for stack in stacks:
        lines.extend(_render_stack(stack))
    lines.extend(
        [
            "",
            "# Declare required env vars here so doctor checks them and",
            "# `initc env` templates .env.example. See the format docs.",
            "# env:",
            "#   - name: SOME_API_KEY",
            "#     secret: true",
        ]
    )
    return "\n".join(lines) + "\n"


def detect_stacks(root: Path) -> list[DetectedStack]:
    """Every stack found at ``root`` or exactly one folder down."""
    candidates = [root]
    candidates.extend(
        folder
        for folder in sorted(root.iterdir())
        if folder.is_dir() and folder.name not in SKIP_DIRS and not folder.name.startswith(".")
    )
    stacks: list[DetectedStack] = []
    for folder in candidates:
        rel = "." if folder == root else folder.name
        for detect in (_detect_python, _detect_node):
            found = detect(folder, rel)
            if found:
                stacks.append(found)
    return _dedupe_names(stacks)


# --- per-language detection ---------------------------------------------------


def _detect_python(folder: Path, rel: str) -> DetectedStack | None:
    dependency_files = tuple(
        name for name in ("pyproject.toml", "requirements.txt") if (folder / name).is_file()
    )
    if not dependency_files:
        return None
    uses_uv = (folder / "uv.lock").is_file()
    tasks: list[tuple[str, str]] = [("install", "uv sync" if uses_uv else "pip install -e .")]
    if (folder / "tests").is_dir():
        tasks.append(("test", "uv run pytest" if uses_uv else "pytest"))
    return DetectedStack(
        name="python" if rel == "." else rel,
        language="python",
        version=_python_version(folder),
        root=rel,
        package_manager="uv" if uses_uv else "pip",
        dependency_files=dependency_files,
        tasks=tuple(tasks),
    )


def _detect_node(folder: Path, rel: str) -> DetectedStack | None:
    package_json = folder / "package.json"
    if not package_json.is_file():
        return None
    try:
        package = json.loads(package_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise DescribeError(f"{package_json} is not valid JSON: {exc}") from exc
    if not isinstance(package, dict):
        raise DescribeError(f"{package_json} must be a JSON object, got {type(package).__name__}")

    manager = "pnpm" if (folder / "pnpm-lock.yaml").is_file() else "npm"
    tasks: list[tuple[str, str]] = [("install", f"{manager} install")]
    scripts = package.get("scripts")
    if isinstance(scripts, dict):
        tasks.extend((name, f"{manager} run {name}") for name in scripts)
    return DetectedStack(
        name="node" if rel == "." else rel,
        language="node",
        version=_node_version(package),
        root=rel,
        package_manager=manager,
        dependency_files=("package.json",),
        tasks=tuple(tasks),
    )


def _python_version(folder: Path) -> str:
    version_file = folder / ".python-version"
    if version_file.is_file():
        first_line = version_file.read_text(encoding="utf-8").strip().splitlines()
        found = VERSION_RE.search(first_line[0]) if first_line else None
        if found:
            return found.group(1)
    pyproject = folder / "pyproject.toml"
    if pyproject.is_file():
        project = _read_pyproject(pyproject).get("project")
        requires = project.get("requires-python", "") if isinstance(project, dict) else ""
        found = VERSION_RE.search(str(requires))
        if found:
            return found.group(1)
    return FILL_ME


def _node_version(package: dict[str, object]) -> str:
    engines = package.get("engines")
    declared = engines.get("node", "") if isinstance(engines, dict) else ""
    found = VERSION_RE.search(str(declared))
    return found.group(1) if found else FILL_ME


def _read_pyproject(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise DescribeError(f"{path} is not valid TOML: {exc}") from exc


def _project_name(root: Path) -> str:
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        project = _read_pyproject(pyproject).get("project")
        name = project.get("name") if isinstance(project, dict) else None
        if isinstance(name, str) and name:
            return name
    package_json = root / "package.json"
    if package_json.is_file():
        try:
            name = json.loads(package_json.read_text(encoding="utf-8")).get("name")
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            name = None
        if isinstance(name, str) and name:
            return name
    return root.resolve().name


# --- rendering ----------------------------------------------------------------


def _render_stack(stack: DetectedStack) -> list[str]:
    todo = "  # TODO: confirm" if stack.version == FILL_ME else ""
    lines = [
        f"  - name: {_yaml_str(stack.name)}",
        f"    language: {stack.language}",
        f'    version: "{stack.version}"{todo}',
    ]
    if stack.root != ".":
        lines.append(f"    root: {_yaml_str(stack.root)}")
    lines.append(f"    package_manager: {stack.package_manager}")
    files = ", ".join(stack.dependency_files)
    lines.append(f"    dependency_files: [{files}]")
    if stack.tasks:
        lines.append("    tasks:  # detected commands - adjust freely")
        lines.extend(f"      {name}: {_yaml_str(command)}" for name, command in stack.tasks)
    return lines


def _dedupe_names(stacks: list[DetectedStack]) -> list[DetectedStack]:
    """Two languages in one folder would collide on the folder-derived name."""
    names = [stack.name for stack in stacks]
    return [
        replace(stack, name=f"{stack.name}-{stack.language}")
        if names.count(stack.name) > 1
        else stack
        for stack in stacks
    ]


def _yaml_str(value: str) -> str:
    """A YAML-safe scalar: JSON string quoting is valid YAML and escapes for us."""
    return json.dumps(value)
