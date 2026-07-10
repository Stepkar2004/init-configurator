"""Runtime path helpers for projects managed by init-configurator.

This is the constructive half of path-lint: the linter forbids absolute paths,
these helpers make the relative ones effortless. Import them in project code:

    from init_configurator.paths import path_to, project_root

    config = project_root() / "config.toml"
    dataset = path_to("data") / "training.csv"

Both work from any current working directory because they anchor on
``project.yaml``, exactly like every ``initc`` command.
"""

from pathlib import Path

from init_configurator.manifest import ManifestError, find_manifest, load_manifest


def project_root(start: Path | None = None) -> Path:
    """The folder containing ``project.yaml`` — anchor every path here."""
    return find_manifest(start).parent


def path_to(name: str, start: Path | None = None) -> Path:
    """Resolve a named directory declared under ``paths:`` in the manifest.

    Raises:
        ManifestError: when ``name`` isn't declared — the message lists what is.
    """
    manifest_path = find_manifest(start)
    manifest = load_manifest(manifest_path)
    if name not in manifest.paths:
        declared = ", ".join(sorted(manifest.paths)) or "(none declared)"
        raise ManifestError(f"no path '{name}' declared in project.yaml — declared: {declared}")
    return manifest_path.parent / manifest.paths[name]
