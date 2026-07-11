# init-configurator

**An agentic project base: skills lead the agent, deterministic tools ground it.**

Start any project from a genome of evolving skills, then keep it honest with a small
CLI that answers, with exit codes and no AI present, the questions that must never
depend on anyone's memory.

- **Skills know HOW** — scaffolding, evolving, and maintaining a project live in
  Markdown skill files a coding agent reads and improves through human-reviewed diffs.
- **Tools know WHETHER** — `initc` checks the facts: is the manifest valid, can this
  machine work here, are the env vars set, did an absolute path sneak in.
- **`project.yaml` records WHAT** — one manifest per repo, the single source of truth.

## Quickstart

One command, nothing installed globally:

```
uvx --from git+https://github.com/Stepkar2004/init-configurator initc spawn my-project
```

`spawn` copies the genome (skills, standards, `docs/` templates) into the target,
**additively — a file that already exists is kept, never overwritten** — so it is safe
on a repo that already has content. Open the folder with your coding agent and the
`bootstrap` skill takes it from there: interview → official scaffolder → `project.yaml`
→ proof by gates. To make the tool a permanent dev dependency of the project:

```
uv add --dev "init-configurator @ git+https://github.com/Stepkar2004/init-configurator"
```

---

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
uv run initc spawn <dir>  # copy the genome into a project; never overwrites
uv run initc describe     # inspect an existing repo, draft its project.yaml
uv run initc validate     # is the manifest well-formed? errors teach, not scold
uv run initc doctor       # is this machine ready? every problem prints its fix
uv run initc run <task>   # run a declared task from anywhere in the tree
uv run initc env          # (re)generate .env.example from the env contract
uv run initc lint-paths   # reject absolute paths (also a pre-commit hook)
uv run initc schema       # export the JSON Schema
```

There is no `init`: scaffolding is done by an agent running the
[`bootstrap` skill](.claude/skills/bootstrap/SKILL.md) against official ecosystem
creators (`uv init`, `create-vite`, …), current at run time and never frozen in a
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

## The genome (SKILLS)

The skills are the part that evolves — few top-level, the less-common procedures
nested as lazy references:

- [**`bootstrap`**](.claude/skills/bootstrap/SKILL.md) — phase 0. Interview → official
  scaffolder → `project.yaml` → proof by gates; per-ecosystem facts (Python, Docker,
  CI, …) load on demand.
- [**`workflow`**](.claude/skills/workflow/SKILL.md) — the everyday SWE loop: plan,
  build, gate, commit. Scaling up and rot-checks (staleness is hunted, not awaited)
  load on demand.
- [**`skill-manager`**](.claude/skills/skill-manager/SKILL.md) — the genome's own
  lifecycle: evolve a skill when a lesson lands, absorb genes from other repos, skill
  authoring standards. Every skill edit is a human-reviewed diff.
- [**`socials`**](.claude/skills/socials/SKILL.md) — shipping visibly: decide →
  optimize → draft → post for any platform, with per-platform playbooks (LinkedIn
  feed mechanics, GitHub discoverability, post visuals). The human always posts.
- [**`project-base`**](.claude/skills/project-base/SKILL.md) — each repo's
  constitution: conventions, gates, module map. Written fresh at bootstrap, then
  evolves with its repo and never syncs back.

The genome ships inside the package — `initc spawn` passes it down to a new project,
and genes can be absorbed back from any repo — gates as selection pressure, diff review
as immunity. Not hypothetical: the first child's improvements (including this skill layout
and `spawn` itself) were absorbed back into the base within a day.

How a coding agent finds its way in any managed repo: root beacon (CLAUDE.md/AGENTS.md)
→ the repo's own `project-base` skill → `project.yaml`.

## Why it's shaped this way

This repo started life as a template scaffolder and was deliberately amputated: across
two adversarial reviews ([docs/reviews/](docs/reviews/)), every defect lived in the
generation layer and none in the verification layer. Templates rot the moment you write
them; deterministic checks do not. The full story and the design that replaced it:
[docs/design/agentic-base.md](docs/design/agentic-base.md).

## Status

Fresh off the pivot (2026-07). The verification tool is hardened — 120 tests, ~94%
coverage, every gate green in CI on both Ubuntu and Windows. The genome passed its
first real test: [traffic-rl](https://github.com/Stepkar2004/traffic-rl) went from an
empty folder to green gates, pre-commit hooks, and CI in one evening — and what it
learned came back as reviewed diffs (the consolidated skill layout and `initc spawn`
itself both originated there).

## License

[MIT](LICENSE) © Stepan Karapetyan
