"""The ``initc`` command-line interface.

Phase 1 ships the manifest commands only; ``init``, ``run``, ``doctor``,
``env``, and ``lint-paths`` land with the next build phases (see
docs/design/manifest-v1.md for the roadmap).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from init_configurator.manifest import Manifest, ManifestError, load_manifest

app = typer.Typer(
    name="initc",
    help="Clone-and-run project setup driven by one project.yaml.",
    no_args_is_help=True,
)

PathArgument = Annotated[
    Path, typer.Argument(help="A project.yaml, or a directory containing one.")
]
SchemaOutOption = Annotated[Path, typer.Option(help="Where to write the JSON Schema.")]


@app.command()
def validate(path: PathArgument = Path(".")) -> None:
    """Check a manifest and print what it declares."""
    try:
        manifest = load_manifest(path)
    except ManifestError as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    stacks = ", ".join(f"{s.name} ({s.language} {s.version})" for s in manifest.stacks)
    typer.echo(f"OK: {manifest.project.name}")
    typer.echo(f"  stacks: {stacks}")
    typer.echo(f"  env vars declared: {len(manifest.env)}")
    typer.echo(f"  extra binaries required: {len(manifest.requires)}")
    typer.echo(f"  docker section: {'yes' if manifest.docker else 'no'}")


@app.command()
def schema(out: SchemaOutOption = Path("schema/project.schema.json")) -> None:
    """Export the manifest's JSON Schema (gives editors autocomplete/validation)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(Manifest.model_json_schema(), indent=2) + "\n", encoding="utf-8")
    typer.echo(f"wrote {out}")


if __name__ == "__main__":
    app()
