"""Starter files that belong to the project rather than to any one language.

The README is not decoration. A scaffolded ``pyproject.toml`` declares
``readme = "README.md"``, and hatchling refuses to build a project whose
declared readme does not exist -- so ``initc init`` failed on every fresh
Python project until the preset wrote one.

The root ``.gitignore`` matters for the same kind of reason. Stack presets
write their ignore file at the STACK root, so a polyglot repo (``web/``,
``api/``) had nothing ignoring the repo-root ``.env`` -- the very file the
generated compose loads.
"""

from init_configurator.manifest import Manifest, Stack

ROOT_GITIGNORE = """\
# Secrets never enter git. The .env.example template does.
.env
.env.*
!.env.example

# OS / editor noise
.DS_Store
"""


def root_files(manifest: Manifest) -> dict[str, str]:
    """Repo-root files that no single stack owns, keyed by root-relative path.

    A stack rooted at ``.`` writes its own README and .gitignore there; the
    caller keeps those (see ``local_mode.plan_files``). These exist so that a
    repo whose stacks all live in subfolders still gets both at the top.
    """
    return {"README.md": readme(manifest), ".gitignore": ROOT_GITIGNORE}


def readme(manifest: Manifest) -> str:
    """The project README: what this is, and the two commands that set it up."""
    description = manifest.project.description or "TODO: one line on what this project does."
    return f"""\
# {manifest.project.name}

{description}

## Setup

```
initc doctor   # is this machine ready? every problem prints its fix
initc init     # scaffold missing files, install everything in-project
```

`project.yaml` is the single source of truth: runtimes, dependency files,
tasks, env vars and data paths are declared there. Change it, then re-run
`initc init` - existing files are never overwritten, so re-running is safe.
"""


def stack_readme(manifest: Manifest, stack: Stack) -> str:
    """README for one stack. A stack at the repo root gets the project README."""
    if stack.root == ".":
        return readme(manifest)
    return f"""\
# {manifest.project.name} - {stack.name}

The {stack.language} stack of {manifest.project.name}.

Setup, tasks, and the env contract are declared for the whole repo one level
up: see `../README.md` and `../project.yaml`.
"""
