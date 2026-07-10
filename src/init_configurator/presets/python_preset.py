"""Starter files for a Python stack: uv/pip, src layout, ruff + mypy strict, pytest.

Core preset only — optional quality add-ons (bandit, interrogate, pip-audit) are
a scaffold-time choice in a later phase, never forced (see docs/design/manifest-v1.md,
"Template vs instance").
"""

from init_configurator.manifest import Manifest, Stack

PYPROJECT_TEMPLATE = """\
[project]
name = "{name}"
version = "0.1.0"
description = "{description}"
readme = "README.md"
requires-python = ">={python_version}"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = [
    "mypy>=1.10",
    "pytest>=8.0",
    "ruff>=0.5",
]

[tool.ruff]
line-length = 100
target-version = "py{version_compact}"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "N", "RUF"]

[tool.mypy]
strict = true

[tool.pytest.ini_options]
addopts = "-ra"
testpaths = ["tests"]
"""

GITIGNORE = """\
# Environments live INSIDE the project but never in git.
.venv/
.env

# Python build/tool caches
__pycache__/
*.py[cod]
dist/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
"""

REQUIREMENTS_STUB = """\
# Dependencies, one per line (installed into ./.venv — never globally).
"""


def files(stack: Stack, manifest: Manifest) -> dict[str, str]:
    """Starter files for one Python stack, keyed by stack-relative path."""
    package = package_name(manifest.project.name)
    major_minor = ".".join(stack.version.split(".")[:2])
    result = {
        f"src/{package}/__init__.py": (
            f'"""{manifest.project.name} package."""\n\n__version__ = "0.1.0"\n'
        ),
        "tests/test_smoke.py": (
            '"""Starter test — replace with real tests as the project grows."""\n'
            "\n"
            f"from {package} import __version__\n"
            "\n"
            "\n"
            "def test_package_imports() -> None:\n"
            "    assert __version__\n"
        ),
        ".gitignore": GITIGNORE,
    }
    # Ensure every dependency file the manifest declares actually exists.
    for dependency_file in stack.dependency_files:
        if dependency_file == "pyproject.toml":
            result["pyproject.toml"] = PYPROJECT_TEMPLATE.format(
                name=manifest.project.name,
                description=manifest.project.description,
                python_version=major_minor,
                version_compact=major_minor.replace(".", ""),
            )
        elif dependency_file.endswith(".txt"):
            result[dependency_file] = REQUIREMENTS_STUB
    return result


def package_name(project_name: str) -> str:
    """Turn a project name into a valid import name: ``my-app`` -> ``my_app``."""
    cleaned = "".join(c if c.isalnum() else "_" for c in project_name.lower())
    return cleaned.lstrip("0123456789_") or "app"
