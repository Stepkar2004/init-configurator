"""Tests for the absolute-path scanner and the path helper lib."""

from pathlib import Path

import pytest

from init_configurator.manifest import ManifestError, PathLint
from init_configurator.path_lint import scan_project
from init_configurator.paths import path_to, project_root

# Built line-by-line so the ignore markers sit in THIS file's source (our own
# path-lint scan skips them) but never inside the scanned tmp file content.
BAD_LINES = "\n".join(
    [
        r"windows = 'G:\data\raw.csv'",  # path-lint: ignore
        "posix = '/home/stepan/models'",  # path-lint: ignore
        r"share = '\\\\nas\\backups'",  # path-lint: ignore
        "home = '~/secrets.txt'",  # path-lint: ignore
        "shell = '$HOME/bin/tool'",  # path-lint: ignore
    ]
)

CLEAN_LINES = "\n".join(
    [
        "url = 'http://localhost:8000/home'",
        "db = 'postgresql://localhost:5432/app'",
        "relative = 'data/raw.csv'",
        "windows_relative = 'data\\\\raw.csv'",
        "ratio = 'nothing:special/here'",
    ]
)

ALL_FILES = PathLint(include=["**/*"], exclude=[])


def scan(
    tmp_path: Path, config: PathLint = ALL_FILES, files: list[Path] | None = None
) -> list[str]:
    return [f"{f.relpath}:{f.line}" for f in scan_project(tmp_path, config, files=files)]


class TestScanner:
    def test_flags_every_absolute_flavor_once_per_line(self, tmp_path: Path) -> None:
        (tmp_path / "bad.py").write_text(BAD_LINES, encoding="utf-8")
        assert scan(tmp_path) == [f"bad.py:{n}" for n in range(1, 6)]

    def test_urls_and_relative_paths_pass(self, tmp_path: Path) -> None:
        (tmp_path / "clean.py").write_text(CLEAN_LINES, encoding="utf-8")
        assert scan(tmp_path) == []

    def test_ignore_marker_skips_the_line(self, tmp_path: Path) -> None:
        line = r"example = 'G:\demo'  # path-lint: ignore"  # path-lint: ignore
        (tmp_path / "docs.py").write_text(line, encoding="utf-8")
        assert scan(tmp_path) == []

    def test_include_globs_limit_the_scan(self, tmp_path: Path) -> None:
        (tmp_path / "bad.py").write_text(BAD_LINES, encoding="utf-8")
        (tmp_path / "bad.log").write_text(BAD_LINES, encoding="utf-8")
        only_python = PathLint(include=["**/*.py"], exclude=[])
        assert scan(tmp_path, only_python) == [f"bad.py:{n}" for n in range(1, 6)]

    def test_top_level_file_matches_double_star_glob(self, tmp_path: Path) -> None:
        (tmp_path / "top.py").write_text(BAD_LINES.splitlines()[0], encoding="utf-8")
        assert scan(tmp_path, PathLint(include=["**/*.py"], exclude=[])) == ["top.py:1"]

    def test_exclude_directory_prefix(self, tmp_path: Path) -> None:
        vendored = tmp_path / "vendor"
        vendored.mkdir()
        (vendored / "bad.py").write_text(BAD_LINES, encoding="utf-8")
        assert scan(tmp_path, PathLint(include=["**/*"], exclude=["vendor/"])) == []

    def test_venv_pruned_even_without_manifest_exclude(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "third_party.py").write_text(BAD_LINES, encoding="utf-8")
        assert scan(tmp_path) == []

    def test_explicit_file_list_still_respects_excludes(self, tmp_path: Path) -> None:
        (tmp_path / "bad.py").write_text(BAD_LINES, encoding="utf-8")
        (tmp_path / "shown.md").write_text(BAD_LINES, encoding="utf-8")
        config = PathLint(include=["**/*"], exclude=["shown.md"])
        listed = [Path("bad.py"), Path("shown.md"), Path("missing.py")]
        assert scan(tmp_path, config, files=listed) == [f"bad.py:{n}" for n in range(1, 6)]


MANIFEST_WITH_PATHS = """\
schema_version: 1
project: {name: demo}
stacks:
  - name: api
    language: python
    version: "3.12"
    package_manager: uv
    dependency_files: [pyproject.toml]
paths:
  data: data/
"""


class TestPathHelpers:
    def test_project_root_from_nested_dir(self, tmp_path: Path) -> None:
        (tmp_path / "project.yaml").write_text(MANIFEST_WITH_PATHS, encoding="utf-8")
        nested = tmp_path / "src" / "deep"
        nested.mkdir(parents=True)
        assert project_root(nested) == tmp_path

    def test_path_to_declared_name(self, tmp_path: Path) -> None:
        (tmp_path / "project.yaml").write_text(MANIFEST_WITH_PATHS, encoding="utf-8")
        assert path_to("data", tmp_path) == tmp_path / "data/"

    def test_path_to_unknown_name_lists_declared(self, tmp_path: Path) -> None:
        (tmp_path / "project.yaml").write_text(MANIFEST_WITH_PATHS, encoding="utf-8")
        with pytest.raises(ManifestError, match="declared: data"):
            path_to("models", tmp_path)
