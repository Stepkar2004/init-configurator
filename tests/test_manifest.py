"""Tests for manifest loading and the teaching quality of its errors."""

from pathlib import Path

import pytest

from init_configurator.manifest import ManifestError, find_manifest, load_manifest

VALID_MANIFEST = """\
schema_version: 1
project:
  name: demo
  description: A demo project.
stacks:
  - name: api
    language: python
    version: "3.12"
    package_manager: uv
    dependency_files: [pyproject.toml]
    tasks:
      test: uv run pytest
env:
  - name: DATABASE_URL
    example: postgresql://localhost:5432/demo
  - name: API_KEY
    required: false
    secret: true
paths:
  data: data/
requires:
  - name: ffmpeg
    reason: audio preprocessing
docker:
  services: ["postgres:16"]
"""


def write_manifest(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "project.yaml"
    path.write_text(content, encoding="utf-8")
    return path


class TestLoadValid:
    def test_full_manifest_parses(self, tmp_path: Path) -> None:
        manifest = load_manifest(write_manifest(tmp_path, VALID_MANIFEST))
        assert manifest.project.name == "demo"
        assert manifest.stacks[0].language == "python"
        assert manifest.stacks[0].tasks["test"] == "uv run pytest"
        assert manifest.env[1].secret is True
        assert manifest.docker is not None

    def test_accepts_directory_containing_manifest(self, tmp_path: Path) -> None:
        write_manifest(tmp_path, VALID_MANIFEST)
        assert load_manifest(tmp_path).project.name == "demo"

    def test_minimal_manifest_defaults(self, tmp_path: Path) -> None:
        minimal = """\
schema_version: 1
project: {name: tiny}
stacks:
  - name: app
    language: node
    version: "24"
    package_manager: pnpm
    dependency_files: [package.json]
"""
        manifest = load_manifest(write_manifest(tmp_path, minimal))
        assert manifest.env == []
        assert manifest.docker is None
        assert manifest.stacks[0].root == "."
        assert manifest.path_lint.include == ["**/*"]


class TestTeachingErrors:
    """Every rejection must say where the problem is and how to fix it."""

    def expect_error(self, tmp_path: Path, content: str) -> str:
        with pytest.raises(ManifestError) as excinfo:
            load_manifest(write_manifest(tmp_path, content))
        return str(excinfo.value)

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(ManifestError, match="manifest not found"):
            load_manifest(tmp_path / "project.yaml")

    def test_unsupported_schema_version(self, tmp_path: Path) -> None:
        broken = VALID_MANIFEST.replace("schema_version: 1", "schema_version: 99")
        message = self.expect_error(tmp_path, broken)
        assert "schema_version 99 is not supported" in message
        assert "upgrade the tool" in message

    def test_unquoted_version_number_gets_yaml_hint(self, tmp_path: Path) -> None:
        broken = VALID_MANIFEST.replace('version: "3.12"', "version: 3.12")
        message = self.expect_error(tmp_path, broken)
        assert 'quote it: version: "3.12"' in message

    def test_env_as_mapping_gets_list_hint(self, tmp_path: Path) -> None:
        broken = """\
schema_version: 1
project: {name: demo}
stacks:
  - name: api
    language: python
    version: "3.12"
    package_manager: uv
    dependency_files: [pyproject.toml]
env:
  DATABASE_URL: required
"""
        message = self.expect_error(tmp_path, broken)
        assert "- name: VAR_NAME" in message

    def test_unknown_key_flagged_as_typo(self, tmp_path: Path) -> None:
        broken = VALID_MANIFEST.replace("stacks:", "stakcs: []\nstacks:")
        message = self.expect_error(tmp_path, broken)
        assert "stakcs" in message
        assert "typo" in message

    def test_unsupported_language_lists_supported_ones(self, tmp_path: Path) -> None:
        broken = VALID_MANIFEST.replace("language: python", "language: ruby")
        message = self.expect_error(tmp_path, broken)
        assert "v1 supports: node, python" in message

    def test_wrong_package_manager_for_language(self, tmp_path: Path) -> None:
        broken = VALID_MANIFEST.replace("package_manager: uv", "package_manager: pnpm")
        message = self.expect_error(tmp_path, broken)
        assert "not supported for python" in message
        assert "uv, pip" in message

    def test_absolute_path_rejected_windows_style(self, tmp_path: Path) -> None:
        broken = VALID_MANIFEST.replace("data: data/", 'data: "G:\\\\data"')  # path-lint: ignore
        message = self.expect_error(tmp_path, broken)
        assert "absolute path" in message

    def test_absolute_path_rejected_posix_style(self, tmp_path: Path) -> None:
        broken = VALID_MANIFEST.replace("data: data/", "data: /home/user/data")  # path-lint: ignore
        message = self.expect_error(tmp_path, broken)
        assert "absolute path" in message

    def test_duplicate_stack_names(self, tmp_path: Path) -> None:
        duplicated = VALID_MANIFEST.replace(
            "stacks:",
            """\
stacks:
  - name: api
    language: node
    version: "24"
    package_manager: pnpm
    dependency_files: [package.json]
""",
        )
        message = self.expect_error(tmp_path, duplicated)
        assert "stack names must be unique" in message

    def test_broken_yaml_reported_as_yaml_problem(self, tmp_path: Path) -> None:
        message = self.expect_error(tmp_path, "schema_version: 1\n  bad indent: [")
        assert "not valid YAML" in message

    def test_non_mapping_yaml(self, tmp_path: Path) -> None:
        message = self.expect_error(tmp_path, "- just\n- a\n- list\n")
        assert "must be a YAML mapping" in message


class TestFindManifest:
    def test_walks_up_from_nested_directory(self, tmp_path: Path) -> None:
        write_manifest(tmp_path, VALID_MANIFEST)
        nested = tmp_path / "src" / "deep" / "deeper"
        nested.mkdir(parents=True)
        assert find_manifest(nested) == tmp_path / "project.yaml"

    def test_missing_everywhere_suggests_init(self, tmp_path: Path) -> None:
        with pytest.raises(ManifestError, match="initc init"):
            find_manifest(tmp_path)
