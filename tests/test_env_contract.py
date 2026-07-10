"""Tests for .env.example generation from the manifest env contract."""

from init_configurator.env_contract import render_env_example
from init_configurator.manifest import Manifest


def manifest_with_env(env: list[dict[str, object]]) -> Manifest:
    return Manifest.model_validate(
        {
            "schema_version": 1,
            "project": {"name": "demo"},
            "stacks": [
                {
                    "name": "api",
                    "language": "python",
                    "version": "3.12",
                    "package_manager": "uv",
                    "dependency_files": ["pyproject.toml"],
                }
            ],
            "env": env,
        }
    )


def test_no_env_vars_means_no_file() -> None:
    assert render_env_example(manifest_with_env([])) is None


def test_required_var_with_example_and_description() -> None:
    content = render_env_example(
        manifest_with_env(
            [{"name": "API_URL", "example": "http://localhost:8000", "description": "Backend."}]
        )
    )
    assert content is not None
    assert "# API_URL (required): Backend." in content
    assert "API_URL=http://localhost:8000" in content


def test_secret_var_never_gets_a_value() -> None:
    content = render_env_example(
        manifest_with_env(
            [{"name": "TOKEN", "required": False, "secret": True, "example": "leaky-value"}]
        )
    )
    assert content is not None
    assert "# TOKEN (optional, secret)" in content
    assert "TOKEN=\n" in content
    assert "leaky-value" not in content


def test_header_says_file_is_generated() -> None:
    content = render_env_example(manifest_with_env([{"name": "X"}]))
    assert content is not None
    assert "edit the manifest, not this file" in content
