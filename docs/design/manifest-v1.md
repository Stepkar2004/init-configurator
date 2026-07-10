# project.yaml — manifest format v1 (design)

Status: APPROVED 2026-07-09 (build order: manifest → local → path-lint → doctor → docker).

## Template vs instance (the abstract-class rule)

init-configurator is GENERIC — it defines the manifest *format* and the machinery that
consumes it. It is the abstract class; every downstream project writes the concrete
instance. Nothing stack- or project-specific ships as a default:

- The example manifest below is what a hypothetical *downstream project* would write.
  Values like `DATABASE_URL` are illustrative instance data, not part of this tool.
- This repo's own `project.yaml` (dogfood) declares only what THIS tool needs:
  one python stack, no env vars, no docker services.
- Stack presets (Ruff config, Biome config, …) are templates the scaffolder offers;
  the "beyond lint" quality tools in them are OPTIONAL add-ons the user picks at init,
  never forced defaults.

## Design goals

1. **One file, single source of truth.** Local setup, Docker generation, `doctor`,
   path-lint, and `.env.example` are all *derived* from the manifest — nothing is
   declared twice.
2. **Human-writable first, agent-writable second.** A beginner fills every required
   field in under a minute; a coding agent can generate it from a prompt.
3. **Root-relative everything.** The directory containing `project.yaml` is the project
   root. Every path in the manifest (and, via path-lint, in the codebase) resolves
   from it.
4. **The manifest stays ignorant of tool configs.** Ruff, Biome, mypy, etc. keep their
   config in their native files (`pyproject.toml`, `biome.json`); the scaffolder writes
   those from per-stack presets. Duplicating them in the manifest would break the
   single-source-of-truth rule for *those tools*.

## The format

Example of a *downstream project's* manifest (see "Template vs instance" above):

```yaml
# project.yaml — single source of truth for this project's setup.
# All paths are relative to this file's directory (= project root).
schema_version: 1

project:
  name: my-app
  description: One-liner used in generated README and docs.

# One entry per language/runtime in the repo. Single-stack repos have exactly one.
stacks:
  - name: api                 # unique label; used in CLI output and compose service names
    language: python          # v1: python | node
    version: "3.12"           # doctor verifies it; docker mode derives the base image
    root: .                   # dir where dependency files and .venv/node_modules live
    package_manager: uv       # python: uv | pip · node: pnpm | npm
    dependency_files: [pyproject.toml]
    tasks:                    # named entry points; `initc run <task>` works from any cwd
      dev: uv run fastapi dev src/app/main.py
      test: uv run pytest

# The .env contract: doctor checks these; `initc env` templates .env.example from them.
env:
  - name: DATABASE_URL
    required: true
    example: postgresql://localhost:5432/app
    description: Primary database connection string.
  - name: OPENAI_API_KEY
    required: false
    secret: true              # doctor never echoes its value; .env.example leaves it blank

# Named data/asset dirs — created at init, exposed via the helper lib: path_to("data").
paths:
  data: data/
  models: models/

# Extra binaries doctor must find, beyond what stacks already imply (python, uv, node…).
requires:
  - name: ffmpeg
    reason: audio preprocessing

# Config for the absolute-path linter (pre-commit hook + CI check).
path_lint:
  include: ["**/*.py", "**/*.ts", "**/*.md"]
  exclude: [".venv/", "node_modules/", "data/"]

# Read ONLY in --docker mode; ignored in local mode.
docker:
  compose: true
  services: [postgres:16]     # sidecar containers added to compose

# Optional: silence named doctor checks this repo deliberately deviates from
# (expo-doctor pattern; every check prints its name in doctor output).
doctor:
  disable: []
```

## Decisions and why (research-backed)

| Decision | Why |
|---|---|
| YAML + root-level `schema_version` | Taskfile (`version: '3'`) and Kubernetes (`apiVersion`) prove the parser itself must branch on an in-document version — no network, no guessing. mise omits one and regrets it. |
| Publish a JSON Schema too | mise/Devbox ship a `$schema` URL → free editor autocomplete/validation. Orthogonal to `schema_version`; we do both. |
| `stacks` is a list | Polyglot repos (py backend + node frontend) are the norm in the portfolio. mise unifies tools+env+tasks in one file at scale — same shape. |
| `tasks` = flat named commands, no DSL | justfile's custom DSL trades away machine validation; Taskfile's YAML tasks + mise tasks prove flat `name: command` covers 95% of needs. v1 runner is a simple subprocess call from project root. |
| `env` is a list of objects | Per-var metadata (`required`, `secret`, `example`, `description`) doesn't fit a flat map. Flox's rule adopted: vars may NOT reference each other (kills ordering bugs). Loader *parses* .env, never `source`s it (direnv's safety lesson). |
| `.env.example` is generated + diffed | dotenv-linter's `diff` pattern: doctor cross-checks manifest env list ↔ `.env.example` keys and flags drift both ways. |
| doctor: pass/warn/fail + fix command per failure | flutter doctor's three-state checklist + brew doctor's "print the remediation, not just the diagnosis". Every check has a name and can be disabled per-repo (expo doctor pattern). Warning bar stays high — brew doctor's over-warning trains users to ignore it. |
| `requires` needs a `reason` | When doctor says "ffmpeg missing", the user immediately knows why it's needed and whether they care. |
| Tool itself is Python | Gemini's Go/Rust advice rejected: this is a Python portfolio, Stepan owns every line (skill rule 1), and the tool shells out to package managers — CLI speed is irrelevant. Python + uv + src layout, dogfooding its own conventions. |

## What the scaffolder writes (per stack preset, NOT stored in manifest)

Each preset writes a small CORE, and nothing else. The add-ons listed under ROADMAP
below are researched but **not implemented in v1** — none of them is written today.

**Python preset (v1, shipped):** uv (in-project `.venv`, `uv.lock`) or pip, `src/`
layout, `README.md`, Ruff lint+format (`E,F,I,B,UP,SIM,N,RUF`), mypy `strict = true`,
pytest, `.gitignore`, a starter test.

**Node preset (v1, shipped):** pnpm pinned via corepack's `packageManager` field —
only when a real pnpm version is detected, since a made-up pin breaks installs (Node
≥25 no longer bundles corepack, so doctor's fix line says to enable it) — Biome as
base linter/formatter, tsconfig extends `@tsconfig/strictest`, Vitest, `README.md`,
`.gitignore`, a starter test. Node 24 LTS pin (revisit Oct 2026 when Node 26 promotes).

**Repo root (v1, shipped):** `README.md`, `.gitignore` (covers `.env`, which the
generated compose loads), `.pre-commit-config.yaml` wiring `initc lint-paths`. A stack
rooted at `.` keeps its own README/.gitignore instead.

**Context beacons (v1, shipped):** CLAUDE.md + AGENTS.md cross-pointing (primary file
per user's agent; the other is a one-line pointer), the instantiated `project-base`
skill, generated `.env.example`, and the `paths:` dirs the manifest declares.

### ROADMAP — researched, not implemented in v1

- **`framework:` on a stack.** Today "React app" is inexpressible: a node stack
  scaffolds a library skeleton whose tsconfig sets no `jsx` and no DOM lib. This is
  the next real feature, and it threads through presets → docker → doctor.
- **Python add-ons:** bandit or Ruff `S` rules (security), interrogate (docstring
  coverage), pip-audit in CI only (it makes a network call — never in pre-commit).
- **Node add-ons:** a narrow-scope ESLint layer for React-only rules
  (`eslint-plugin-react-hooks` recommended preset — includes React Compiler
  diagnostics — plus `eslint-plugin-jsx-a11y`), Playwright e2e, **knip** (dead
  exports/deps — ts-prune is deprecated and archived), **dependency-cruiser**
  (enforceable architecture/import rules), **size-limit** (CI bundle budget).
- **Generated CI workflow.** The pre-commit hook is generated; the workflow is not,
  because a downstream CI job has to be able to install init-configurator first.
  Blocked on publishing this repo.
- **`project_root()` for other languages.** The helper lib is Python-only, so for
  Node/Go/Rust the constructive half of path-lint does not exist yet.

Add-ons stay opt-in by design (the abstract-class rule above): the generic template
must not force a security scanner or a bundle budget onto a project that never asked.

**Hooks orchestration:** pre-commit (Python-based) is the single hook manager even in
polyglot repos — init-configurator already guarantees Python exists, and one manager
beats husky+pre-commit fighting over `.git/hooks`.

## CLI surface (v1)

```
initc init [--docker] [--skip-install] [--agent agents|claude]
                                # scaffold from project.yaml; local install is the default,
                                # --docker generates Dockerfile/compose instead
initc doctor                    # verify binaries/versions/env contract; ok/warn/fail
initc run <task> [--stack NAME] # run a manifest task from anywhere in the tree
initc env                       # (re)generate .env.example; diff against manifest
initc lint-paths [FILES...]     # absolute-path scan (also a pre-commit hook)
initc validate [PATH]           # check a manifest and print what it declares
initc schema [--out PATH]       # export the JSON Schema
```

### Doctor check names

Every check prints its name, and `doctor.disable` in the manifest takes those names.
`<stack>` is a stack's `name`; `<pm>` its `package_manager`.

| Name | Checks |
|---|---|
| `binary:<pm>` | the package manager is on PATH |
| `runtime:<stack>` | the declared runtime exists and matches `version` (uv stacks warn, don't fail — uv fetches the interpreter) |
| `deps:<stack>:<file>` | each declared dependency file exists |
| `install:<stack>` | the in-project env (`.venv` / `node_modules`) exists — warn, not fail |
| `requires:<name>` | an extra binary from `requires:` is on PATH |
| `env:<VAR>` | a required env var is set (shell env or `.env`) |
| `env-sync` | `.env.example` matches the manifest's env list, both directions |

## Build order (scope v1, approved 2026-07-09)

1. Manifest: pydantic models, loader, validation errors that teach, JSON Schema export.
2. Local mode: scaffold + in-project envs, presets, context beacons.
3. Path-lint: scanner + `project_root()` helper lib (py first, js later) + pre-commit hook.
4. Doctor: binary/version checks, env contract diff, three-state report.
5. Docker mode: Dockerfile + compose generated from manifest (last — not needed until
   downstream projects ship).
```
