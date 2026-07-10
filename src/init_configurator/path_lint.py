"""Path-lint: reject machine-absolute paths so clones run anywhere.

A hardcoded Windows drive path, a /home-style prefix, a UNC share, or a
home-directory reference works on exactly one machine. This scanner flags them
all; the fix is always the same — resolve from the project root (see
``init_configurator.paths.project_root``).

Two escape hatches, both deliberate:

- a line containing ``path-lint: ignore`` is skipped (for docs and tests that
  legitimately SHOW absolute paths);
- the manifest's ``path_lint.include``/``exclude`` globs (fnmatch-style)
  control which files are scanned at all.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from init_configurator.manifest import PathLint

MARKER = "path-lint: ignore"

# Directories that are never worth scanning, whatever the manifest says.
ALWAYS_PRUNED = frozenset(
    {
        ".git",
        ".venv",
        "node_modules",
        "dist",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
    }
)

PATTERNS = (
    # Windows drive path. The (?!/) keeps URL schemes like http:// out.
    re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/](?!/)"),
    # UNC network share.
    re.compile(r"\\\\[A-Za-z0-9_.$-]+\\"),
    # POSIX absolute prefixes that always mean "someone's machine".
    re.compile(r"(?<![\w.])/(?:home|Users|usr|etc|var|opt|tmp|root|mnt|srv)/"),  # path-lint: ignore
    # Home-directory references (tilde, HOME, USERPROFILE).  # path-lint: ignore
    re.compile(r"(?<![\w])~[\\/]|\$HOME/|%USERPROFILE%"),  # path-lint: ignore
)


@dataclass(frozen=True)
class Finding:
    """One absolute path found in one line of one file."""

    relpath: str
    line: int
    match: str

    def __str__(self) -> str:
        return (
            f"{self.relpath}:{self.line}: absolute path '{self.match}' - "
            f"resolve from the project root instead (project_root() helper), "
            f"or append '{MARKER}' if this line must show one"
        )


def scan_project(root: Path, config: PathLint, files: list[Path] | None = None) -> list[Finding]:
    """Scan the tree (or just ``files``, as pre-commit passes them) for findings."""
    candidates = _explicit_files(root, files) if files is not None else _walk(root)
    findings: list[Finding] = []
    for path, relpath in candidates:
        if _matches(relpath, config.include) and not _excluded(relpath, config.exclude):
            findings.extend(scan_file(path, relpath))
    return findings


def scan_file(path: Path, relpath: str) -> list[Finding]:
    """Scan one text file; unreadable/binary files are silently skipped."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    findings = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if MARKER in line:
            continue
        for pattern in PATTERNS:
            found = pattern.search(line)
            if found:
                findings.append(Finding(relpath=relpath, line=line_number, match=found.group()))
                break  # one finding per line is enough to fail; keep output short
    return findings


def _walk(root: Path) -> list[tuple[Path, str]]:
    """All scannable files as (absolute path, posix relpath), pruned early."""
    result = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ALWAYS_PRUNED]
        for filename in filenames:
            path = Path(dirpath) / filename
            result.append((path, path.relative_to(root).as_posix()))
    return result


def _explicit_files(root: Path, files: list[Path]) -> list[tuple[Path, str]]:
    """Resolve a pre-commit style file list against the project root."""
    result = []
    for file in files:
        path = file if file.is_absolute() else root / file
        if path.is_file():
            result.append((path, path.resolve().relative_to(root.resolve()).as_posix()))
    return result


def _matches(relpath: str, patterns: list[str]) -> bool:
    """fnmatch with one convenience: '**/*.py' also matches top-level 'x.py'."""
    return any(
        fnmatch(relpath, pattern)
        or (pattern.startswith("**/") and fnmatch(relpath, pattern.removeprefix("**/")))
        for pattern in patterns
    )


def _excluded(relpath: str, patterns: list[str]) -> bool:
    """Exclude entries ending in '/' are directory prefixes; others are globs."""
    for pattern in patterns:
        if pattern.endswith("/") and relpath.startswith(pattern):
            return True
        if fnmatch(relpath, pattern):
            return True
    return False
