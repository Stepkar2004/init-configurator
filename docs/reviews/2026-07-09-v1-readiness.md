# v1 readiness review — 2026-07-09

Scope: full review of docs, skills, folder layout, test organization, and the scaffold's
readiness to self-adjust per language and framework. Findings were verified by running the
CLI end-to-end against fresh throwaway projects, not by reading alone.

Repo state at review time: `initc run test|lint|typecheck` and `initc lint-paths` all green;
73 tests passing; `schema/project.schema.json` in sync with the pydantic model.

---

## Summary

**The chassis is genuinely good. The scaffold output is not yet a good start — and the
headline promise is currently false.**

The single most important finding: **`initc init` exits 1 on a brand-new Python project.**
The scaffolded `pyproject.toml` declares `readme = "README.md"`, but the scaffolder never
writes a README, so hatchling fails during `uv sync`. A/B tested on two identical fresh
directories — without a README, exit 1; with one, exit 0. For a tool whose README opens with
*"Clone any project. Run one command. It works,"* this matters more than every other item
combined.

**Tests folder — does not need organizing.** Eight flat files mirroring eight source modules
is correct at this size; flat `tests/` matches flat `src/`. Splitting into
`unit/`/`integration/` now would be ceremony. The real problems are different: there is no
`conftest.py`, so the same manifest fixture is hand-rolled in five files, and there is **no
test of `cli.py` at all** — no `CliRunner`, no end-to-end scaffold→install→run test. The
product *is* a CLI, and the CLI is the one thing with zero coverage. That is why the README
bug shipped.

**Docs — the problem is not that there is too little, it is that what exists is wrong.**
`docs/` has one file and it has drifted from the code. It documents an `initc init --local`
flag that does not exist (running it errors), and README line 5 repeats the claim. It
advertises optional add-ons (bandit, knip, Playwright, a React ESLint layer) as "picked at
init" — none are implemented. Adding more documents before fixing these makes the showcase
worse, not better.

**Ready for Go / Rust / React? No, on both axes.** Language dispatch is an
`if language == "python": ... else: <node>` chain repeated across five modules. Four of the
five would silently give a Go stack *Node* behavior; the fifth (`doctor.py:117`) is a bare
dict lookup that raises an uncaught `KeyError`. The framework dimension **does not exist at
all** — there is no `framework` field, so "React app" is inexpressible. Scaffolding React
today yields a library skeleton whose `tsconfig` cannot compile JSX.

**Skills — not lacking skills; there is a skill *identity* bug.** One well-written skill is
the right number. But the checked-in `SKILL.md` announces itself as "CANONICAL TEMPLATE —
other repos instantiate this," while downstream repos actually receive a *different* skill
generated inside `beacons.py`. Two divergent sources of truth — and the generated one tells
the agent *"no absolute paths, ever (pre-commit + CI enforce it)"*, which is false, because
`initc init` writes neither a pre-commit config nor a CI workflow.

---

## 1. The blocker: `initc init` fails on a fresh Python project

`python_preset.py:15` emits `readme = "README.md"` into the scaffolded `pyproject.toml`. The
`files()` function never writes a README. So `uv sync` builds the project, hatchling validates
metadata, and dies:

```
OSError: Readme file does not exist: README.md
ERROR: uv sync (app) failed with exit code 1
```

Reproduced on two clean directories differing only by a pre-seeded `README.md`:
`noreadme -> exit=1`, `withreadme -> exit=0`.

Two fixes, both wanted. Scaffold a `README.md` — the project-base skill's rule 4 already says
*"a milestone isn't done until README shows it"*, so every generated project should start with
one. And add the end-to-end test that would have caught this.

Related quiet failure: this is also why a first `initc init` leaves a half-built `.venv`
behind. `uv` creates the venv before the build step fails, so the project is left in a state
where `doctor` reports `install: ok` while nothing is actually installed.

## 2. What the scaffolder actually produces

Verified by scaffolding a polyglot React+Python project (`--docker`) and a single-stack
Python project.

**Root `.env` is not gitignored in any multi-stack project.** The `.gitignore` comes from the
*stack preset*, so it lands at `web/.gitignore` and `api/.gitignore` — neither covers the repo
root. But `.env.example` is written at the root, and the generated `compose.yaml` points at a
root `.env` via `env_file: [.env]`. Confirmed with `git status`: a root `.env` shows up as an
addable untracked file. That is a credential-leak path in the default polyglot flow.

(Initially suspected `node_modules` had the same problem. Re-tested: it does not. That was a
false alarm from probing a nonexistent directory — a trailing-slash gitignore pattern only
matches a real directory.)

**Scaffolded projects get no path-lint enforcement.** Nothing in `src/` ever writes a
`.pre-commit-config.yaml` or a `.github/workflows/` file. Yet `beacons.py:109` writes into
every downstream skill: *"`initc lint-paths` — no absolute paths, ever (pre-commit + CI
enforce it)."* Nothing enforces it. The flagship differentiator ships to downstream repos as
an honor system, and the agent instructions assert otherwise.
`docs/design/manifest-v1.md:135` also lists "path-lint pre-commit hook + CI workflow" and
"`docs/` and `tests/` dirs" among the context beacons — the `docs/` dir is not created either.

**Docker mode does not produce a runnable app.** The generated `compose.yaml` for a
web+api+postgres project has no `ports:` on any service (nothing is reachable from the host),
no `depends_on`, no volume for postgres (data vanishes), and — critically — `postgres:16` with
no `POSTGRES_PASSWORD`, which makes the official image refuse to start. The web `Dockerfile`
is single-stage with no build step, and its `CMD` is `pnpm preview`, which binds a loopback
address inside the container. So `initc init --docker && docker compose up` gives a failed
database and an unreachable frontend.

**`.dockerignore` is ineffective for any stack whose `root` is not `.`.** It is written once
at the repo root, but compose sets `build.context: web`, and Docker only reads `.dockerignore`
from the build context root. Multi-stack images will copy in `node_modules` and `.venv`.

## 3. Extensibility: the language axis

Five dispatch points, no registry:

| Location | Behavior on an unknown language |
|---|---|
| `manifest.py:82` | `Literal["python","node"]` rejects it |
| `presets/__init__.py:18` | falls into the `else` → **Node preset** |
| `local_mode.py:113` | falls into the `else` → `<pm> install` |
| `docker_mode.py:56` | falls into the `else` → **Node Dockerfile** |
| `doctor.py:117` | `RUNTIME_BINARY[lang]` → **uncaught KeyError** |
| `doctor.py:162` | `.venv if python else "node_modules"` → looks for `node_modules` in a Rust repo |

Adding Go means editing seven files and eleven branch points, and the failure mode of
forgetting one is *silently wrong output*, not an error.

Two additional sync hazards. `Stack.language` and the `PACKAGE_MANAGERS` dict are independent
declarations that must be updated together — miss one and the validator itself `KeyError`s.
And `schema/project.schema.json` is generated but hand-committed with **no CI drift check**;
verified currently in sync, but nothing guarantees it stays that way.

The fix is one refactor: a `LanguageProvider` registry, one object per language carrying
`runtime_binary`, `install_dir`, `package_managers`, `install_steps()`, `dockerfile_body()`,
and `preset_files()`. Derive the `Literal` and `PACKAGE_MANAGERS` from the registry keys.
Adding Go becomes "register one provider," and the `else` branches — the real bug factory —
disappear entirely.

Noted separately: `path_to()` / `project_root()` live in the `init_configurator` package, so a
downstream Python project must take init-configurator (and pydantic, typer, pyyaml) as a
**runtime production dependency** to use them. The design doc's "js later" never happened — so
for Node, Go, and Rust the constructive half of path-lint does not exist. Also,
`find_manifest()` anchors on the current working directory, so `project_root()` in a deployed
service depends on where it was launched from, not where the module lives.

## 4. Extensibility: the framework axis

This axis does not exist yet, and it is the bigger gap for the stated goal. `Stack` carries
`name, language, version, root, package_manager, dependency_files, tasks` — nothing about
frameworks. `scaffold_files()` takes no framework parameter.

Concretely, a React scaffold today gets: `src/index.ts` exporting a `greeting` constant; a
`tsconfig` extending `@tsconfig/strictest` with **no `jsx` setting and no DOM lib**, so a
`.tsx` file will not compile; `"build": "tsc"` instead of `vite build`; Vitest with no jsdom
environment; and no `react`/`react-dom` dependencies. The never-overwrite rule means these
files *stick*, so if `initc init` runs before Vite scaffolds, the result is a library skeleton
to clean up by hand.

If "become a React project" is a real goal, `framework: str | None` on `Stack`, threaded into
presets → docker → doctor, is the design change. It is a bigger commitment than the language
registry, and should be sequenced second.

## 5. Docs, drift, and structure

Doc drift, all verified against source:

- `initc init --local` (README:5, `manifest-v1.md:140`) — **no such flag**; running it errors
  with `No such option: --local`. Local is the default.
- "or interactively create one" (`manifest-v1.md:140`) — no interactive path exists.
- `paths.data` (`manifest-v1.md:69`) — the real API is `path_to("data")`.
- Optional add-ons (`manifest-v1.md:117-127`) — bandit, interrogate, pip-audit, knip,
  dependency-cruiser, size-limit, Playwright, React ESLint: **none implemented**. Both preset
  docstrings defer them to "a later phase."
- The design doc's "CLI surface (v1)" omits `validate` and `schema`, which ship.
- **Doctor check names are documented nowhere**, so `doctor: disable:` is unusable without
  reading source. The seven patterns are `binary:<pm>`, `runtime:<stack>`,
  `deps:<stack>:<file>`, `install:<stack>`, `requires:<name>`, `env:<VAR>`, `env-sync`.
- `pyproject.toml:7` declares `license = "MIT"`. **There is no LICENSE file.** For a public
  showcase repo this is the first thing a reviewer checks.

Structure is fine and should be left alone. Eleven flat modules in `src/` are legible;
`cli.py` stays properly thin (every command is find → load → delegate → echo). No directory is
over-populated.

What should actually change in `tests/`: add a `conftest.py` with a `build_manifest` factory —
the same python/uv stack dict is copy-pasted verbatim across `test_docker_mode.py:11`,
`test_doctor.py:20`, `test_env_contract.py:7`, `test_local_mode.py:9`, and
`test_runner.py:11`. Add `tests/test_cli.py` with `CliRunner`. Fold away the 7-line
`test_smoke.py`.

Two repo-hygiene notes. `pytest-cov` is a dev dependency and `[tool.coverage]` is fully
configured in `pyproject.toml:47-52` — and **nothing ever runs it**; `addopts = "-ra"` has no
`--cov` and CI runs bare `pytest`. And `.pre-commit-hooks.yaml` exists (the *provider* file, so
other repos can consume the hook) but there is no `.pre-commit-config.yaml`, so **this repo
does not run its own hook**. CI is also Ubuntu-only while development happens on Windows, and
`local_mode.py:133` has a `sys.platform == "win32"` branch that CI never exercises.

A small polish item that will bite in a demo: console output is full of em-dashes, and Windows
stdout is `cp1252`. Every teaching error message currently prints mojibake on the development
platform — `unknown key <?> likely a typo`. `doctor.py` already avoids this deliberately
("plain ASCII on purpose"); `manifest.py` and `path_lint.py` do not.

## 6. Recommended order

1. Scaffold a `README.md`, and add `tests/test_cli.py` with a real `initc init` round-trip.
   This is the difference between a tool that works and one that does not.
2. Write a root `.gitignore` (covering `.env`) independent of stack presets.
3. Add `LICENSE`. Delete the `--local` claim from README and the design doc.
4. Make `initc init` write `.pre-commit-config.yaml` + a CI workflow — or stop claiming in the
   generated skill that they enforce anything.
5. Reconcile the two skills: the checked-in file is this repo's dogfood copy, the template
   lives in `beacons.py`. Say so in the header.
6. Fix compose (`ports`, `depends_on`, postgres password/volume) and move `.dockerignore` into
   each build context.
7. Then the `LanguageProvider` registry, with a CI schema-drift check. Go and Rust become one
   file each.
8. Then `framework:`, if React is a genuine target rather than an aspiration.

Items 1–3 are what stand between this and a repo worth handing an interviewer. Everything from
7 down is the interesting engineering, and it is much safer to do once a CLI test exists.
