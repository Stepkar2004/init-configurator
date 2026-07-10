"""Tests for .env.example generation from the manifest env contract."""

from typing import Any

from init_configurator.env_contract import render_env_example
from init_configurator.manifest import Manifest
from tests.conftest import ManifestFactory


def with_env(build_manifest: ManifestFactory, env: list[dict[str, Any]]) -> Manifest:
    return build_manifest(env=env)


def test_no_env_vars_means_no_file(build_manifest: ManifestFactory) -> None:
    assert render_env_example(with_env(build_manifest, [])) is None


def test_required_var_with_example_and_description(build_manifest: ManifestFactory) -> None:
    manifest = with_env(
        build_manifest,
        [{"name": "API_URL", "example": "http://localhost:8000", "description": "Backend."}],
    )
    content = render_env_example(manifest)
    assert content is not None
    assert "# API_URL (required): Backend." in content
    assert "API_URL=http://localhost:8000" in content


def test_secret_var_never_gets_a_value(build_manifest: ManifestFactory) -> None:
    manifest = with_env(
        build_manifest,
        [{"name": "TOKEN", "required": False, "secret": True, "example": "leaky-value"}],
    )
    content = render_env_example(manifest)
    assert content is not None
    assert "# TOKEN (optional, secret)" in content
    assert "TOKEN=\n" in content
    assert "leaky-value" not in content


def test_header_says_file_is_generated(build_manifest: ManifestFactory) -> None:
    content = render_env_example(with_env(build_manifest, [{"name": "X"}]))
    assert content is not None
    assert "edit the manifest, not this file" in content
