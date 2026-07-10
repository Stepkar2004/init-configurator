"""Tests for the runtime registry.

The point of the registry is that a language's checks live in exactly one
place. These tests fail loudly when a language is only half-added -- declared
in the manifest but never registered, or registered with package managers the
manifest would reject.
"""

from pathlib import Path
from typing import get_args

import pytest

from init_configurator.manifest import PACKAGE_MANAGERS, SUPPORTED_LANGUAGES, PackageManager
from init_configurator.runtimes import RUNTIMES, runtime_for


def test_every_declarable_language_has_a_runtime() -> None:
    assert set(RUNTIMES) == set(SUPPORTED_LANGUAGES)


def test_package_manager_tables_agree() -> None:
    # doctor prints a runtime's fix for a manifest-validated package manager,
    # so a manager the manifest allows must be one the runtime can explain.
    for language, runtime in RUNTIMES.items():
        assert set(runtime.package_manager_fix) == set(PACKAGE_MANAGERS[language])


def test_the_package_manager_literal_covers_every_language_table() -> None:
    # The Literal is what puts an enum in the exported JSON Schema; the tables
    # are what the validator reads. A manager in one and not the other is either
    # undeclarable or unvalidated.
    declarable = {manager for managers in PACKAGE_MANAGERS.values() for manager in managers}
    assert frozenset(get_args(PackageManager)) == declarable


def test_unregistered_language_is_a_loud_bug_not_node_behavior() -> None:
    with pytest.raises(KeyError, match="no entry"):
        runtime_for("rust")


def test_runtime_binaries_and_install_dirs() -> None:
    assert runtime_for("python").runtime_binary == "python"
    assert runtime_for("python").install_dir == ".venv"
    assert runtime_for("node").runtime_binary == "node"
    assert runtime_for("node").install_dir == "node_modules"


class TestInstallOk:
    """`install_dir` existing says something started, not that it finished."""

    def test_python_wants_pyvenv_cfg_not_just_a_directory(self, tmp_path: Path) -> None:
        runtime = runtime_for("python")
        (tmp_path / ".venv").mkdir()
        assert not runtime.install_ok(tmp_path)  # an interrupted `python -m venv`
        (tmp_path / ".venv" / "pyvenv.cfg").write_text(
            "include-system-site-packages = false\n", encoding="utf-8"
        )
        assert runtime.install_ok(tmp_path)

    def test_node_wants_a_non_empty_node_modules(self, tmp_path: Path) -> None:
        runtime = runtime_for("node")
        modules = tmp_path / "node_modules"
        modules.mkdir()
        assert not runtime.install_ok(tmp_path)  # what a failed install leaves
        (modules / "vitest").mkdir()
        assert runtime.install_ok(tmp_path)
