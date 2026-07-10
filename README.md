# init-configurator

An agentic project base: **skills lead the agent, deterministic tools ground it.**

One `project.yaml` per repo declares what the project IS — stacks, tasks, env contract,
data paths. A small Python tool answers, with exit codes and no AI present, the
questions that must never depend on anyone's memory: *is the manifest valid? can this
machine work here? are the env vars set? did an absolute path sneak in?* Everything
about *creating* the project lives in evolving skill files
([.claude/skills/](.claude/skills/)) that a coding agent reads, follows, and — through
human-reviewed diffs — improves.

**Skills know HOW. Tools know WHETHER. `project.yaml` records WHAT.**

This repo started life as a template scaffolder and was deliberately amputated: across
two adversarial reviews ([docs/reviews/](docs/reviews/)), every defect lived in the
generation layer and none in the verification layer. The full story and the design that
replaced it: [docs/design/agentic-base.md](docs/design/agentic-base.md).

## The manifest

One `project.yaml` at the repo root is the single source of truth. Format spec:
[docs/design/manifest-v1.md](docs/design/manifest-v1.md); a published
[JSON Schema](schema/project.schema.json) gives editors autocomplete and validation.

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
      install: uv sync
      test: uv run pytest
```

## The tool

```
uv run initc describe     # inspect an existing repo, draft its project.yaml
uv run initc validate     # is the manifest well-formed? errors teach, not scold
uv run initc doctor       # is this machine ready? every problem prints its fix
uv run initc run <task>   # run a declared task from anywhere in the tree
uv run initc env          # (re)generate .env.example from the env contract
uv run initc lint-paths   # reject absolute paths (also a pre-commit hook)
uv run initc schema       # export the JSON Schema
```

There is no `init`. Scaffolding is done by an agent running the
[`bootstrap` skill](.claude/skills/bootstrap/SKILL.md) against official ecosystem
creators (`uv init`, `create-vite`, …) — current at run time, never frozen in a
template. Installing is a declared task like any other: `initc run install`.

doctor borrows from the best: three-state results like flutter doctor, a fix printed
next to every problem like brew doctor, named per-repo-disableable checks like expo
doctor:

```
  ok    binary:uv - uv 0.11.12
  ok    runtime:cli - python 3.12.5 matches '3.12'
  ok    deps:cli:pyproject.toml - pyproject.toml present
  warn  install:cli - ./.venv not created yet (or left half-installed)
        fix: initc run install
Doctor: 3 ok, 1 warnings, 0 problems
```

path-lint's constructive half is the helper lib — the linter forbids absolute paths,
these make relative ones effortless from any working directory:

```python
from init_configurator import path_to, project_root

config = project_root() / "config.toml"   # anchored on project.yaml, like git finds .git
dataset = path_to("data") / "raw.csv"     # named dirs declared under paths: in the manifest
```

Lines that must SHOW an absolute path (docs, tests) append `path-lint: ignore`.

## The genome

The skills are the part that evolves. Lessons become procedures through a
human-reviewed diff (`evolve`); a manager skill owns consolidation and decay
(`skill-manager`); staleness is hunted, not awaited (`rot-check`); and the whole genome
can be passed to a new project (`spawn`) or extracted from any existing repo (`absorb`)
— gates as selection pressure, diff review as immunity.

How a coding agent finds its way in any managed repo: root beacon (CLAUDE.md/AGENTS.md)
→ the repo's own `project-base` skill → `project.yaml`.

## License

[MIT](LICENSE) © Stepan Karapetiani
