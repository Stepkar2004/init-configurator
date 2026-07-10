# Repo structure — what every file is for

> Written 2026-07-10, the day of the amputation. One sentence per folder, a line per
> file. If this file disagrees with reality, `rot-check` treats that as a failing check.

## Root

| File | What it is |
|---|---|
| `CLAUDE.md` | The constitution: how to think here, always loaded in full, points at everything else. |
| `AGENTS.md` | One-line pointer at CLAUDE.md so any non-Claude agent finds its way. |
| `README.md` | The public face: the line ("skills know HOW, tools know WHETHER"), the CLI, the pivot story. |
| `LICENSE` | MIT. |
| `project.yaml` | This repo's own manifest — the tool dogfoods its own format (stack, gates as tasks, path-lint config). |
| `pyproject.toml` | The tool's packaging: deps, ruff/mypy/pytest config, the `initc` entry point. |
| `uv.lock` | Locked dependency versions; the actual pin behind every `>=` floor. |
| `.gitattributes` | `* text=auto eol=lf` — what the code writes LF, git must not rewrite CRLF on checkout. |
| `.gitignore` | Keeps `.venv`, caches, and `.env` out of git. |
| `.pre-commit-config.yaml` | This repo runs its own path-lint hook plus ruff check/format on every commit. |
| `.pre-commit-hooks.yaml` | The other half: lets ANY repo consume `initc lint-paths` as a pre-commit hook. |
| `.github/workflows/ci.yml` | The gates in CI on Ubuntu + Windows, plus the schema-drift check. |

## `.claude/skills/` — the genome

Skills are the evolving HOW; each is markdown an agent loads only when it triggers, and
every edit to one is a human-reviewed diff.

| Skill | What it does |
|---|---|
| `project-base/SKILL.md` | Binds every session in THIS repo: gates, conventions, module map, chunk discipline, env rule, lessons. |
| `bootstrap/SKILL.md` | Phase 0 of any project: interview → official creator → project.yaml → beacons → hooks → prove with gates. |
| `bootstrap/references/python.md` | Python stack knowledge: uv-first creator, ruff/mypy/pytest baseline, pip's dependency-group traps, LF rule. |
| `bootstrap/references/node.md` | Node/TS knowledge: pnpm/packageManager pinning, strictest tsconfig split, biome's two traps, corepack's death. |
| `bootstrap/references/react.md` | Frontend rule (always the framework's own creator, never a vendored template) + narrow React lint layer. |
| `bootstrap/references/docker.md` | Container knowledge: pinned bases, strict lockfile COPY, frozen installs, compose/sidecar rules. |
| `bootstrap/references/quality-tools.md` | The opt-in menu (vulture, radon, knip, dependency-cruiser, …) — offered, never defaulted. |
| `evolve/SKILL.md` | The one door for self-modification: lesson → procedure (not anecdote) → altitude → trust mark → reviewed diff. |
| `skill-manager/SKILL.md` | Global hygiene over all skills: altitude smells, consolidation, the miss-log triage, self-set thresholds. |
| `scale/SKILL.md` | When work outgrows one context: the four moves, five stress patterns, chunk definition, cold-start quiz. |
| `absorb/SKILL.md` | Conjugation: absorb genes from any repo (with provenance + review), spawn this genome into a new project. |
| `rot-check/SKILL.md` | The staleness hunt: watch every gate fail, stale-pin sweep, docs truth pass, trust decay. |

## `src/init_configurator/` — the tool

Deterministic, runs with no AI present; answers WHETHER, never HOW.

| Module | What it answers |
|---|---|
| `__init__.py` | Public API: `Manifest`, `load_manifest`, `find_manifest`, `path_to`, `project_root`. |
| `manifest.py` | Is `project.yaml` well-formed? Pydantic models + validation errors that teach the fix. |
| `doctor.py` | Can this machine work here? ok/warn/fail checks, every problem prints its remediation. |
| `runtimes.py` | Per-language checks ONLY: runtime binary, install dir, what a finished install looks like. |
| `describe.py` | What does this existing repo contain? Drafts a manifest deterministically; `FILL_ME` marks its gaps. |
| `env_contract.py` | Templates `.env.example` from the declared env contract; secrets never get values. |
| `runner.py` | Runs a declared task from anywhere in the tree, cwd pinned to the stack root. |
| `path_lint.py` | Rejects machine-absolute paths (the destructive half of the path story). |
| `paths.py` | `project_root()` / `path_to()` — makes relative paths effortless (the constructive half). |
| `beacons.py` | Template source for a downstream project's CLAUDE.md/AGENTS.md + project-base skill. |
| `textfile.py` | Every generated file is written LF explicitly, because `write_text` translates newlines. |
| `cli.py` | The `initc` surface: `describe · validate · doctor · env · run · lint-paths · schema`. |
| `py.typed` | PEP 561 marker: this package ships type information. |

## `schema/`

| File | What it is |
|---|---|
| `project.schema.json` | Generated JSON Schema of the manifest — gives editors autocomplete/validation; CI fails if it drifts from the models. |

## `tests/` — flat, 1:1 with modules

| File | Covers |
|---|---|
| `__init__.py` | Makes `tests` a package so files can import `tests.conftest` types. |
| `conftest.py` | Shared manifest/stack factories. |
| `test_cli.py` | Every command as a user runs it, incl. the describe → validate round trip. |
| `test_manifest.py` | Loading, validation, and the teaching quality of every error. |
| `test_doctor.py` | Three-state checks, fixes, disables, env contract sync. |
| `test_runtimes.py` | Registry ↔ manifest agreement; install_ok semantics. |
| `test_describe.py` | Detection rules, FILL_ME honesty, drafts that pass load_manifest. |
| `test_env_contract.py` | .env.example rendering, secret blanking. |
| `test_path_lint.py` | The absolute-path scanner and its ignore marker. |
| `test_beacons.py` | The downstream templates speak the post-pivot CLI (no `initc init` can sneak back). |
| `test_runner.py` | Task lookup, disambiguation, teaching errors. |
| `test_console_output.py` | Everything printed to a terminal is ASCII (Windows cp1252 consoles). |

## `docs/`

| Path | What it is |
|---|---|
| `vision.md` | The human-owned WHY — structure ready, content awaiting Stepan; only he edits it. |
| `state/now.md` | Where the project is right now; updated at every chunk boundary. |
| `state/roadmap.md` | Ordered next chunks, derived from the vision. |
| `state/log.md` | One entry per chunk, newest first — the project's memory of what happened. |
| `state/miss-log.md` | One line per task that matched no skill — how the genome notices its own gaps. |
| `decisions/0001-amputate-the-scaffolder.md` | ADR recording the pivot: what was cut, why, consequences. |
| `design/agentic-base.md` | THE design document: why we stopped, the line, the organs, scaling, honest limits, the tree. |
| `design/manifest-v1.md` | The manifest format spec (verification half stands; generation half marked history). |
| `reviews/` | The two adversarial reviews — the evidence that caused the pivot, kept verbatim. |
| `structure.md` | This file. |
