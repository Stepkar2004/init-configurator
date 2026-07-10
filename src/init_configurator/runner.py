"""Run manifest tasks (``initc run test``) from anywhere inside the project.

Tasks are plain shell strings owned by the project author, so they run through
the shell on purpose. The working directory is always the stack's root — the
command behaves identically no matter how deep in the tree it was invoked from.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from init_configurator.manifest import Manifest, ManifestError, Stack, find_manifest, load_manifest


def find_task(manifest: Manifest, task: str, stack_name: str | None = None) -> Stack:
    """Locate the single stack declaring ``task``; errors teach, as always.

    Raises:
        ManifestError: when the task is unknown (lists what exists) or exists
            in several stacks (says how to disambiguate).
    """
    candidates = [stack for stack in manifest.stacks if task in stack.tasks]
    if stack_name is not None:
        candidates = [stack for stack in candidates if stack.name == stack_name]
    if not candidates:
        available = sorted(
            f"{stack.name}:{name}" for stack in manifest.stacks for name in stack.tasks
        )
        listing = ", ".join(available) if available else "(none declared)"
        raise ManifestError(f"no task '{task}' in project.yaml — available: {listing}")
    if len(candidates) > 1:
        names = ", ".join(stack.name for stack in candidates)
        raise ManifestError(
            f"task '{task}' exists in several stacks ({names}) — "
            f"pick one with: initc run {task} --stack <name>"
        )
    return candidates[0]


def run_task(task: str, stack_name: str | None = None, start: Path | None = None) -> int:
    """Execute a task and return its exit code (the CLI passes it through)."""
    manifest_path = find_manifest(start)
    manifest = load_manifest(manifest_path)
    stack = find_task(manifest, task, stack_name)
    cwd = (manifest_path.parent / stack.root).resolve()
    return subprocess.run(stack.tasks[task], shell=True, cwd=cwd).returncode
