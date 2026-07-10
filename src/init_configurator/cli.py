"""The ``initc`` command-line interface.

Implemented: ``init`` (local mode), ``run``, ``env``, ``validate``, ``schema``.
Still to land, in build order: ``lint-paths``, ``doctor``, and docker mode
(see docs/design/manifest-v1.md for the roadmap).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from init_configurator import local_mode
from init_configurator.beacons import PrimaryChoice
from init_configurator.env_contract import write_env_example
from init_configurator.manifest import Manifest, ManifestError, find_manifest, load_manifest
from init_configurator.runner import run_task

app = typer.Typer(
    name="initc",
    help="Clone-and-run project setup driven by one project.yaml.",
    no_args_is_help=True,
)

PathArgument = Annotated[
    Path, typer.Argument(help="A project.yaml, or a directory containing one.")
]
SchemaOutOption = Annotated[Path, typer.Option(help="Where to write the JSON Schema.")]
AgentOption = Annotated[
    str,
    typer.Option(
        "--agent",
        help="Which agent file is primary: 'agents' (AGENTS.md) or 'claude' (CLAUDE.md).",
    ),
]


def _fail(error: Exception) -> typer.Exit:
    typer.echo(f"ERROR: {error}", err=True)
    return typer.Exit(code=1)


@app.command()
def init(
    docker: Annotated[
        bool, typer.Option("--docker", help="Generate docker setup instead.")
    ] = False,
    skip_install: Annotated[
        bool, typer.Option("--skip-install", help="Scaffold only; don't install anything.")
    ] = False,
    agent: AgentOption = "agents",
) -> None:
    """Materialize project.yaml: scaffold missing files and install in-project."""
    if docker:
        typer.echo(
            "ERROR: docker mode is not built yet — it lands last "
            "(after local mode, path-lint, and doctor). Use local mode for now.",
            err=True,
        )
        raise typer.Exit(code=1)
    if agent not in ("agents", "claude"):
        raise _fail(ValueError("--agent must be 'agents' or 'claude'"))
    primary: PrimaryChoice = "claude" if agent == "claude" else "agents"

    try:
        manifest_path = find_manifest()
        manifest = load_manifest(manifest_path)
        report = local_mode.initialize(
            manifest, manifest_path.parent, skip_install=skip_install, agent=primary
        )
    except (ManifestError, local_mode.SetupError) as exc:
        raise _fail(exc) from exc

    for line in report:
        typer.echo(f"  {line}")
    typer.echo(f"OK: {manifest.project.name} is set up locally")


@app.command()
def run(
    task: Annotated[str, typer.Argument(help="A task name declared in project.yaml.")],
    stack: Annotated[
        str | None, typer.Option(help="Stack name, when several declare the task.")
    ] = None,
) -> None:
    """Run a manifest task from anywhere inside the project."""
    try:
        exit_code = run_task(task, stack_name=stack)
    except ManifestError as exc:
        raise _fail(exc) from exc
    raise typer.Exit(code=exit_code)


@app.command()
def env() -> None:
    """(Re)generate .env.example from the manifest's env contract."""
    try:
        manifest_path = find_manifest()
        manifest = load_manifest(manifest_path)
    except ManifestError as exc:
        raise _fail(exc) from exc
    written = write_env_example(manifest, manifest_path.parent)
    if written is None:
        typer.echo("no env vars declared in project.yaml — nothing to generate")
    else:
        typer.echo(f"wrote {written.name} ({len(manifest.env)} vars)")


@app.command()
def validate(path: PathArgument = Path(".")) -> None:
    """Check a manifest and print what it declares."""
    try:
        manifest = load_manifest(path)
    except ManifestError as exc:
        raise _fail(exc) from exc

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
