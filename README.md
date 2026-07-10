# init-configurator

Clone any project. Run one command. It works.

- **Two install modes:** local by default (everything inside the project folder — venv,
  local node_modules; zero global installs), or `--docker` (generated Dockerfile/compose)
- **path-lint:** a check that rejects absolute paths — root-relative or it doesn't merge.
  Ships as a pre-commit hook, scaffolded into every project init touches
- **`initc doctor`:** tells you what's missing *before* setup fails, not during
- **`.env` contract:** required vars declared in the manifest, checked, templated

## The manifest

One `project.yaml` at the repo root is the single source of truth — every feature above
derives from it. Format spec and rationale: [docs/design/manifest-v1.md](docs/design/manifest-v1.md).
A published [JSON Schema](schema/project.schema.json) gives editors autocomplete and
inline validation.

```yaml
schema_version: 1
project:
  name: my-app
stacks:
  - name: api
    language: python
    version: "3.12"
    package_manager: uv
    dependency_files: [pyproject.toml]
    tasks:
      test: uv run pytest
```

## Try it today

```
uv sync
uv run initc init         # scaffold missing files + install everything in-project
uv run initc run test     # run a manifest task from anywhere in the tree
uv run initc env          # (re)generate .env.example from the manifest
uv run initc doctor       # what's missing, what's misconfigured, and how to fix it
uv run initc lint-paths   # reject absolute paths (also a pre-commit hook)
uv run initc validate     # checks the manifest, prints what it declares
uv run initc schema       # exports the JSON Schema
```

path-lint's constructive half is the helper lib — the linter forbids absolute paths,
these make relative ones effortless from any working directory:

```python
from init_configurator import path_to, project_root

config = project_root() / "config.toml"   # anchored on project.yaml, like git finds .git
dataset = path_to("data") / "raw.csv"     # named dirs declared under paths: in the manifest
```

Lines that must SHOW an absolute path (docs, tests) append `path-lint: ignore`. This
repo's own scanner caught the regex that detects `$HOME` — that line now carries the
marker it inspired.

`initc init` never overwrites an existing file — re-running it is always safe. It also
drops the agent context beacons: the file your coding agent reads natively (CLAUDE.md or
AGENTS.md, pick with `--agent`) gets the full instructions; the other becomes a one-line
pointer, so every agent finds its way.

Validation errors teach instead of scold — every problem names its exact spot in the
file and, where the mistake is guessable, adds a fix hint (e.g. unquoted `version: 3.12`
→ *"YAML reads an unquoted 3.12 as a number — quote it"*).

doctor borrows from the best: three-state results like flutter doctor (ok / warn /
fail — "will break" and "worth knowing" stay distinct), a fix printed next to every
problem like brew doctor, and named, per-repo-disableable checks like expo doctor:

```
  ok    binary:uv - uv 0.11.12
  ok    runtime:cli - python 3.12.5 matches '3.12'
  ok    deps:cli:pyproject.toml - pyproject.toml present
  warn  install:cli - ./.venv not created yet
        fix: initc init
Doctor: 3 ok, 1 warnings, 0 problems
```

## Docker mode

`initc init --docker` scaffolds the same starter files, skips local installs, and
generates one Dockerfile per stack (dependency layer cached separately from source,
CMD taken from the manifest's `start` task) plus a `compose.yaml` wiring your stacks
and declared sidecars (`services: ["postgres:16"]`). Each stack gets its own
`.dockerignore`, because Docker reads that file only from the build context root.
Sidecars come up first (`depends_on`), and a declared postgres arrives with the password
its image demands plus a named volume, so the database outlives the container. Ports are
yours to pick — compose can't guess them, so it says so instead of guessing. Generated
docker files follow the same rule as everything else: never overwritten, so hand edits
stick.

## How a coding agent finds its way (the discovery chain)

Every scaffolded project carries three layers of agent context, each pointing deeper:

1. **CLAUDE.md / AGENTS.md** at the root — your agent's native file has the full
   instructions, the other is a pointer (`--agent` picks which).
2. **`.claude/skills/project-base/SKILL.md`** — the instantiated project skill: setup
   workflow, ground rules, and a lessons section that grows with the repo.
3. **`project.yaml`** — the single source of truth everything derives from.

Adding a language is adding one object: a provider in `languages.LANGUAGES` carrying its
runtime binary, install dir, package managers, starter files, install steps, and
Dockerfile body. A test asserts the registry and the manifest can't disagree.

Status: v1 feature-complete — manifest ✅ · local mode ✅ · path-lint ✅ · doctor ✅ ·
docker mode ✅. Next: publish prep (remote, demo screencasts).
Demo screencasts (fresh-machine clone → running, both modes) land here when v1 ships.

## License

[MIT](LICENSE) © Stepan Karapetiani
