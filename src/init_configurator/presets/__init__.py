"""Starter files for each supported stack.

A preset answers one question: "this stack was declared in project.yaml but its
files don't exist yet — what should be written?" Presets return plain
``{relative_path: content}`` mappings and never touch the filesystem; deciding
what is missing and writing it is local_mode's job. Existing files are never
overwritten.
"""

from init_configurator.manifest import Manifest, Stack
from init_configurator.presets import node_preset, python_preset


def scaffold_files(
    stack: Stack, manifest: Manifest, *, pnpm_version: str | None = None
) -> dict[str, str]:
    """Return the starter files for one stack, keyed by stack-relative path."""
    if stack.language == "python":
        return python_preset.files(stack, manifest)
    return node_preset.files(stack, manifest, pnpm_version=pnpm_version)
