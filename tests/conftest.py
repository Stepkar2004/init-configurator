"""Shared test fixtures: one manifest factory instead of five hand-rolled copies.

Exposed as fixtures rather than importable helpers, so test modules never have
to import from ``conftest`` -- pytest injects them by parameter name.

Every factory returns a fresh deep copy: tests routinely mutate the manifest
they are handed (swapping a package manager, appending a dependency file), and
a shared dict would leak those edits into the next test.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

import pytest

from init_configurator.manifest import Manifest

PYTHON_STACK: dict[str, Any] = {
    "name": "api",
    "language": "python",
    "version": "3.12",
    "package_manager": "uv",
    "dependency_files": ["pyproject.toml"],
    "tasks": {"test": "uv run pytest", "start": "uv run python -m demo"},
}

NODE_STACK: dict[str, Any] = {
    "name": "web",
    "language": "node",
    "version": "24",
    "root": "frontend/",
    "package_manager": "pnpm",
    "dependency_files": ["package.json"],
    "tasks": {"test": "pnpm test"},
}

StackFactory = Callable[..., dict[str, Any]]
ManifestFactory = Callable[..., Manifest]


@pytest.fixture
def python_stack() -> StackFactory:
    """A uv/Python stack at the repo root; keyword args override any field."""
    return lambda **overrides: {**copy.deepcopy(PYTHON_STACK), **overrides}


@pytest.fixture
def node_stack() -> StackFactory:
    """A pnpm/Node stack rooted at ``frontend/``; keyword args override any field."""
    return lambda **overrides: {**copy.deepcopy(NODE_STACK), **overrides}


@pytest.fixture
def build_manifest() -> ManifestFactory:
    """Validate a minimal manifest; keyword args replace whole top-level sections."""

    def _build(**overrides: Any) -> Manifest:
        base: dict[str, Any] = {
            "schema_version": 1,
            "project": {"name": "demo-app", "description": "A demo."},
            "stacks": [copy.deepcopy(PYTHON_STACK)],
        }
        base.update(overrides)
        return Manifest.model_validate(base)

    return _build
