"""The ``initc`` command-line interface.

The tool answers questions; it does not write your project. Surface:
``validate``, ``doctor``, ``env``, ``run``, ``lint-paths``, ``schema``,
``describe`` (draft a manifest for an existing repo), and ``spawn`` (copy the
packaged genome into a project, additively; ``--force`` updates existing
skills). Generation belongs to an agent
guided by ``.claude/skills/`` -- see docs/design/agentic-base.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from init_configurator.describe import DescribeError, render_draft
from init_configurator.doctor import format_results, has_failures, run_doctor
from init_configurator.env_contract import write_env_example
from init_configurator.manifest import (
    MANIFEST_FILENAME,
    Manifest,
    ManifestError,
    find_manifest,
    load_manifest,
)
from init_configurator.path_lint import scan_project
from init_configurator.runner import run_task
from init_configurator.spawn import SpawnError, spawn_genome
from init_configurator.textfile import write_text_lf

app = typer.Typer(
    name="initc",
    help="Deterministic checks for a project described by one project.yaml.",
    no_args_is_help=True,
)

PathArgument = Annotated[
    Path, typer.Argument(help="A project.yaml, or a directory containing one.")
]
DescribeArgument = Annotated[Path, typer.Argument(help="The repo to inspect.")]
SchemaOutOption = Annotated[Path, typer.Option(help="Where to write the JSON Schema.")]
SpawnArgument = Annotated[
    Path, typer.Argument(help="The project folder to receive the genome (created if missing).")
]
ForceOption = Annotated[
    bool,
    typer.Option(
        "--force",
        help="Overwrite existing skill files with the base's version. "
        "Docs, standards, and skills the base does not ship stay untouched.",
    ),
]


def _fail(error: Exception) -> typer.Exit:
    typer.echo(f"ERROR: {error}", err=True)
    return typer.Exit(code=1)


@app.command()
def describe(path: DescribeArgument = Path(".")) -> None:
    """Inspect an existing repo and draft the project.yaml that describes it."""
    root = path.resolve()
    target = root / MANIFEST_FILENAME
    if target.exists():
        raise _fail(
            ValueError(
                f"{target} already exists - describe never overwrites; "
                f"edit the manifest directly (it is the source of truth)"
            )
        )
    try:
        draft = render_draft(root)
    except DescribeError as exc:
        raise _fail(exc) from exc
    write_text_lf(target, draft)
    typer.echo(f"drafted {MANIFEST_FILENAME} from what {root.name}/ already contains")
    typer.echo("review every line (FILL_ME marks the gaps), then: initc validate")


@app.command()
def spawn(path: SpawnArgument = Path("."), force: ForceOption = False) -> None:
    """Copy the genome into a project; additive by default, --force updates existing skills."""
    try:
        results = spawn_genome(path, force_skills=force)
    except SpawnError as exc:
        raise _fail(exc) from exc
    labels = {"added": "added   ", "replaced": "replaced", "kept": "kept    "}
    for spawned in results:
        typer.echo(f"  {labels[spawned.outcome]} {spawned.target}")
    counts = {outcome: 0 for outcome in labels}
    for spawned in results:
        counts[spawned.outcome] += 1
    typer.echo(
        f"spawned the genome into {path}: "
        f"{counts['added']} added, {counts['replaced']} replaced, {counts['kept']} kept"
    )
    if counts["kept"] and not force:
        typer.echo(
            "kept files existed before and were not touched - "
            "rerun with --force to update existing skills, or merge by hand"
        )
    typer.echo("next: run the bootstrap skill (.claude/skills/bootstrap/SKILL.md)")


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
        typer.echo("no env vars declared in project.yaml - nothing to generate")
    else:
        typer.echo(f"wrote {written.name} ({len(manifest.env)} vars)")


@app.command()
def doctor() -> None:
    """Check binaries, versions, files, and the env contract; fail before work does."""
    try:
        manifest_path = find_manifest()
        manifest = load_manifest(manifest_path)
    except ManifestError as exc:
        raise _fail(exc) from exc

    results = run_doctor(manifest, manifest_path.parent)
    for line in format_results(results):
        typer.echo(line)
    if has_failures(results):
        raise typer.Exit(code=1)


@app.command(name="lint-paths")
def lint_paths(
    files: Annotated[
        list[Path] | None,
        typer.Argument(
            help="Specific files to scan (as pre-commit passes them); default: whole tree."
        ),
    ] = None,
) -> None:
    """Scan for absolute paths; exit 1 when any are found."""
    try:
        manifest_path = find_manifest()
        manifest = load_manifest(manifest_path)
    except ManifestError as exc:
        raise _fail(exc) from exc

    findings = scan_project(manifest_path.parent, manifest.path_lint, files=files)
    for finding in findings:
        typer.echo(str(finding), err=True)
    if findings:
        plural = "s" if len(findings) != 1 else ""
        typer.echo(f"FAIL: {len(findings)} absolute path{plural} found", err=True)
        raise typer.Exit(code=1)
    typer.echo("OK: no absolute paths found")


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


@app.command()
def schema(out: SchemaOutOption = Path("schema/project.schema.json")) -> None:
    """Export the manifest's JSON Schema (gives editors autocomplete/validation)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    write_text_lf(out, json.dumps(Manifest.model_json_schema(), indent=2) + "\n")
    typer.echo(f"wrote {out}")


if __name__ == "__main__":
    app()
