"""Tests for the language registry.

The point of the registry is that a language is described in exactly one place.
These tests fail loudly when a language is only half-added -- declared in the
manifest but never registered, or registered with package managers the manifest
would reject.
"""

from pathlib import Path

import pytest

from init_configurator.languages import LANGUAGES, provider_for
from init_configurator.manifest import PACKAGE_MANAGERS, SUPPORTED_LANGUAGES
from tests.conftest import ManifestFactory, StackFactory


def test_every_declarable_language_has_a_provider() -> None:
    assert set(LANGUAGES) == set(SUPPORTED_LANGUAGES)


def test_package_manager_tables_agree() -> None:
    # doctor prints a provider's fix for a manifest-validated package manager,
    # so a manager the manifest allows must be one the provider can explain.
    for language, provider in LANGUAGES.items():
        assert set(provider.package_manager_fix) == set(PACKAGE_MANAGERS[language])


def test_unregistered_language_is_a_loud_bug_not_node_behavior() -> None:
    with pytest.raises(KeyError, match="no provider"):
        provider_for("rust")


class TestProviderBehavior:
    def test_python_provider(
        self, build_manifest: ManifestFactory, python_stack: StackFactory
    ) -> None:
        manifest = build_manifest(stacks=[python_stack()])
        stack = manifest.stacks[0]
        provider = provider_for("python")
        assert provider.runtime_binary == "python"
        assert provider.install_dir == ".venv"
        assert "pyproject.toml" in provider.preset_files(stack, manifest)
        assert provider.install_steps(stack, Path("api"))[0].argv == ("uv", "sync")
        assert "FROM python:3.12-slim" in provider.dockerfile_body(stack)

    def test_node_provider(self, build_manifest: ManifestFactory, node_stack: StackFactory) -> None:
        manifest = build_manifest(stacks=[node_stack()])
        stack = manifest.stacks[0]
        provider = provider_for("node")
        assert provider.runtime_binary == "node"
        assert provider.install_dir == "node_modules"
        assert "package.json" in provider.preset_files(stack, manifest, pnpm_version="10.5.0")
        assert provider.install_steps(stack, Path("web"))[0].argv == ("pnpm", "install")
        assert "FROM node:24-slim" in provider.dockerfile_body(stack)
