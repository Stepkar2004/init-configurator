# init-configurator

Clone any project. Run one command. It works.

- **Two install modes:** `--docker` (generated Dockerfile/compose) or `--local`
  (everything inside the project folder — venv, local node_modules; zero global installs)
- **path-lint:** pre-commit + CI check that rejects absolute paths — root-relative or it
  doesn't merge
- **`init doctor`:** tells you what's missing *before* setup fails, not during
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
uv run initc validate     # checks the manifest, prints what it declares
uv run initc schema       # exports the JSON Schema
```

`initc init` never overwrites an existing file — re-running it is always safe. It also
drops the agent context beacons: the file your coding agent reads natively (CLAUDE.md or
AGENTS.md, pick with `--agent`) gets the full instructions; the other becomes a one-line
pointer, so every agent finds its way.

Validation errors teach instead of scold — every problem names its exact spot in the
file and, where the mistake is guessable, adds a fix hint (e.g. unquoted `version: 3.12`
→ *"YAML reads an unquoted 3.12 as a number — quote it"*).

Status: v1 in progress — manifest ✅ · local mode ✅ · path-lint · doctor · docker mode.
Demo screencasts (fresh-machine clone → running, both modes) land here when v1 ships.
