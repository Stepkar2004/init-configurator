"""init-configurator: clone-and-run setup for any project.

One ``project.yaml`` manifest per repo declares languages, dependency files,
entry-point tasks, required env vars, and data paths. Everything the tool does
(local install, docker generation, doctor checks, path linting) is derived
from that single file.
"""

from init_configurator.manifest import (
    Manifest,
    ManifestError,
    find_manifest,
    load_manifest,
)
from init_configurator.paths import path_to, project_root

__version__ = "0.1.0"

__all__ = [
    "Manifest",
    "ManifestError",
    "__version__",
    "find_manifest",
    "load_manifest",
    "path_to",
    "project_root",
]
