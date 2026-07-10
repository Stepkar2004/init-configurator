"""Everything printed to a terminal must be ASCII.

Windows consoles still default to cp1252. An em-dash in an error message renders
as mojibake there -- `unknown key <?> likely a typo` -- which is exactly the
moment a beginner most needs the message to read cleanly. doctor.py already said
"plain ASCII on purpose"; this makes that a rule the whole CLI is held to.

Modules that WRITE files (beacons, env_contract) are exempt: their strings
become UTF-8 file contents, never console output. describe.py both writes and
prints, so it is held to the rule -- its draft is ASCII anyway.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from init_configurator import path_lint, runner
from init_configurator.manifest import ManifestError, load_manifest
from tests.conftest import ManifestFactory

SRC = Path(__file__).resolve().parents[1] / "src" / "init_configurator"

PRINTING_MODULES = [
    "cli.py",
    "describe.py",
    "doctor.py",
    "manifest.py",
    "path_lint.py",
    "paths.py",
    "runner.py",
    "runtimes.py",
]


def _docstrings(tree: ast.Module) -> set[int]:
    """Ids of the Constant nodes that are docstrings, which may keep their typography."""
    documented = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    found: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, documented) or not node.body:
            continue
        first = node.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            found.add(id(first.value))
    return found


@pytest.mark.parametrize("filename", PRINTING_MODULES)
def test_no_non_ascii_string_literals(filename: str) -> None:
    tree = ast.parse((SRC / filename).read_text(encoding="utf-8"))
    skip = _docstrings(tree)
    offenders = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in skip
        and not node.value.isascii()
    ]
    assert offenders == [], f"{filename} has non-ASCII console strings: {offenders}"


class TestRenderedMessages:
    def test_a_validation_error_is_ascii_end_to_end(self, tmp_path: Path) -> None:
        (tmp_path / "project.yaml").write_text(
            "schema_version: 1\nproject: {name: demo}\nstacks:\n"
            "  - name: api\n    language: python\n    version: 3.12\n"
            "    package_manager: uv\n    dependency_files: [pyproject.toml]\n"
            "    typo_key: oops\n",
            encoding="utf-8",
        )
        with pytest.raises(ManifestError) as caught:
            load_manifest(tmp_path)
        message = str(caught.value)
        assert message.isascii(), message
        assert "quote it" in message  # the unquoted 3.12 hint still lands
        assert "likely a typo" in message  # and so does the unknown-key hint

    def test_a_path_lint_finding_is_ascii(self) -> None:
        finding = path_lint.Finding(relpath="loader.py", line=3, match="C:/")  # path-lint: ignore
        assert str(finding).isascii()

    def test_a_runner_error_is_ascii(self, build_manifest: ManifestFactory) -> None:
        with pytest.raises(ManifestError) as caught:
            runner.find_task(build_manifest(), "deploy")
        assert str(caught.value).isascii()
