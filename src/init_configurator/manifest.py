"""Load and validate ``project.yaml`` — the single source of truth.

Every feature of init-configurator (local install, docker generation, doctor,
path-lint, ``.env.example``) derives from the manifest defined here. The
directory containing ``project.yaml`` IS the project root; every path in the
manifest must be relative to it.

Validation errors are written to teach: each problem names the exact spot in
the file and, where we can guess the mistake, adds a hint for fixing it.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from pydantic_core import ErrorDetails

MANIFEST_FILENAME = "project.yaml"
SUPPORTED_SCHEMA_VERSIONS = frozenset({1})

# Which package managers make sense for each language (v1 scope).
PACKAGE_MANAGERS: dict[str, tuple[str, ...]] = {
    "python": ("uv", "pip"),
    "node": ("pnpm", "npm"),
}


class ManifestError(Exception):
    """A manifest could not be found, parsed, or validated.

    The message is end-user-facing: it points at the problem location and
    suggests a fix where possible.
    """


def _reject_absolute(value: str) -> str:
    """Reject absolute paths regardless of the OS the check runs on.

    A manifest written on Windows must still validate on Linux (CI, docker),
    so both path flavors are checked, plus ``~`` home expansion.
    """
    is_absolute = (
        PureWindowsPath(value).is_absolute()
        or PurePosixPath(value).is_absolute()
        or value.startswith("~")
        # A lone drive letter like "C:" is not absolute to pathlib but still
        # escapes the project root.
        or PureWindowsPath(value).drive != ""
    )
    if is_absolute:
        raise ValueError(
            f"'{value}' is an absolute path — manifest paths must be relative "
            f"to the project root (the folder containing {MANIFEST_FILENAME})"
        )
    return value


class StrictModel(BaseModel):
    """Base for all manifest sections: unknown keys are errors, not surprises."""

    model_config = ConfigDict(extra="forbid")


class ProjectInfo(StrictModel):
    """The ``project:`` section — identity used in generated files."""

    name: str = Field(min_length=1)
    description: str = ""


class Stack(StrictModel):
    """One language/runtime in the repo (the ``stacks:`` list).

    Single-language repos have exactly one stack; a py-backend + node-frontend
    repo has two.
    """

    name: str = Field(min_length=1)
    language: Literal["python", "node"]
    version: str = Field(min_length=1)
    root: str = "."
    package_manager: str
    dependency_files: list[str] = Field(min_length=1)
    tasks: dict[str, str] = {}

    _root_is_relative = field_validator("root")(_reject_absolute)

    @model_validator(mode="after")
    def _package_manager_matches_language(self) -> Stack:
        allowed = PACKAGE_MANAGERS[self.language]
        if self.package_manager not in allowed:
            raise ValueError(
                f"package_manager '{self.package_manager}' is not supported for "
                f"{self.language} — pick one of: {', '.join(allowed)}"
            )
        return self


class EnvVar(StrictModel):
    """One entry of the ``env:`` contract.

    Doctor checks these against the real environment / ``.env``, and
    ``initc env`` templates ``.env.example`` from them. Entries may not
    reference each other — declarations stay order-independent.
    """

    name: str = Field(min_length=1)
    required: bool = True
    description: str = ""
    example: str = ""
    secret: bool = False  # never echoed by doctor; blank value in .env.example


class Requirement(StrictModel):
    """An extra binary doctor must find (``requires:`` list).

    ``reason`` is mandatory so "ffmpeg missing" always comes with a why.
    """

    name: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class PathLint(StrictModel):
    """Config for the absolute-path linter (``path_lint:`` section)."""

    include: list[str] = ["**/*"]
    exclude: list[str] = []


class DockerConfig(StrictModel):
    """The ``docker:`` section — read only in ``--docker`` mode."""

    compose: bool = True
    services: list[str] = []


class DoctorConfig(StrictModel):
    """The ``doctor:`` section — per-repo tuning of doctor checks.

    Every doctor check has a name (printed in its output line); a repo that
    deliberately deviates lists those names here instead of ignoring the whole
    report — the expo-doctor lesson.
    """

    disable: list[str] = []


class Manifest(StrictModel):
    """The whole ``project.yaml`` file."""

    schema_version: int
    project: ProjectInfo
    stacks: list[Stack] = Field(min_length=1)
    env: list[EnvVar] = []
    paths: dict[str, str] = {}
    requires: list[Requirement] = []
    path_lint: PathLint = PathLint()
    docker: DockerConfig | None = None
    doctor: DoctorConfig = DoctorConfig()

    @field_validator("schema_version")
    @classmethod
    def _schema_version_is_supported(cls, value: int) -> int:
        if value not in SUPPORTED_SCHEMA_VERSIONS:
            supported = ", ".join(str(v) for v in sorted(SUPPORTED_SCHEMA_VERSIONS))
            raise ValueError(
                f"schema_version {value} is not supported by this init-configurator "
                f"(supported: {supported}) — upgrade the tool, or write the manifest "
                f"against a supported version"
            )
        return value

    @field_validator("paths")
    @classmethod
    def _paths_are_relative(cls, value: dict[str, str]) -> dict[str, str]:
        for name, path in value.items():
            try:
                _reject_absolute(path)
            except ValueError as exc:
                raise ValueError(f"paths.{name}: {exc}") from exc
        return value

    @model_validator(mode="after")
    def _names_are_unique(self) -> Manifest:
        stack_names = [stack.name for stack in self.stacks]
        duplicates = {name for name in stack_names if stack_names.count(name) > 1}
        if duplicates:
            raise ValueError(f"stack names must be unique, found duplicates: {duplicates}")
        env_names = [var.name for var in self.env]
        duplicates = {name for name in env_names if env_names.count(name) > 1}
        if duplicates:
            raise ValueError(f"env var names must be unique, found duplicates: {duplicates}")
        return self


def find_manifest(start: Path | None = None) -> Path:
    """Walk up from ``start`` (default: cwd) to the nearest ``project.yaml``.

    This is how every command locates the project root, so all of them work
    from any subdirectory — the same trick git uses to find ``.git``.

    Raises:
        ManifestError: if no manifest exists anywhere up the tree.
    """
    directory = (start or Path.cwd()).resolve()
    for candidate_dir in (directory, *directory.parents):
        candidate = candidate_dir / MANIFEST_FILENAME
        if candidate.is_file():
            return candidate
    raise ManifestError(
        f"no {MANIFEST_FILENAME} found in {directory} or any parent folder — "
        f"run 'initc init' to create one, or cd into a project that has one"
    )


def load_manifest(path: Path) -> Manifest:
    """Read and validate a manifest from a file or a directory containing one.

    Raises:
        ManifestError: with a teaching, location-specific message on any
            problem — missing file, broken YAML, or failed validation.
    """
    manifest_path = path / MANIFEST_FILENAME if path.is_dir() else path
    if not manifest_path.is_file():
        raise ManifestError(f"manifest not found: {manifest_path}")

    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ManifestError(f"{manifest_path} is not valid YAML:\n{exc}") from exc

    if not isinstance(raw, dict):
        raise ManifestError(
            f"{manifest_path} must be a YAML mapping (key: value pairs), got {type(raw).__name__}"
        )

    try:
        return Manifest.model_validate(raw)
    except ValidationError as exc:
        raise ManifestError(_render_validation_error(manifest_path, exc)) from exc


def _render_validation_error(manifest_path: Path, error: ValidationError) -> str:
    """Turn pydantic's error list into location-specific lines with hints."""
    problems = error.errors()
    plural = "s" if len(problems) != 1 else ""
    lines = [f"{manifest_path} is invalid ({len(problems)} problem{plural}):"]
    for problem in problems:
        location = _format_location(problem["loc"]) or "(top level)"
        lines.append(f"  - {location}: {problem['msg']}")
        hint = _hint_for(problem)
        if hint:
            lines.append(f"      hint: {hint}")
    return "\n".join(lines)


def _format_location(loc: tuple[int | str, ...]) -> str:
    """Render a pydantic error location like ``stacks[0].tasks.dev``."""
    parts: list[str] = []
    for item in loc:
        if isinstance(item, int):
            parts.append(f"[{item}]")
        else:
            parts.append(f".{item}" if parts else str(item))
    return "".join(parts)


def _hint_for(problem: ErrorDetails) -> str | None:
    """Best-effort fix suggestion for the most common manifest mistakes."""
    error_type = problem["type"]
    loc = problem["loc"]
    last = loc[-1] if loc else None

    if error_type == "extra_forbidden":
        return "unknown key — likely a typo; compare against docs/design/manifest-v1.md"
    if last == "version" and error_type == "string_type":
        return 'YAML reads an unquoted 3.12 as a number — quote it: version: "3.12"'
    if last == "env" and error_type == "list_type":
        return "env is a list of entries, each starting with '- name: VAR_NAME'"
    if last == "language":
        supported = ", ".join(sorted(PACKAGE_MANAGERS))
        return f"v1 supports: {supported}"
    if last == "schema_version" and error_type == "missing":
        return "add 'schema_version: 1' at the top of the file"
    if error_type == "missing":
        return f"add the required key '{last}'"
    return None
