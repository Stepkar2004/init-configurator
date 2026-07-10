# Standards, rot, and release readiness — 2026-07-09

Second review, taken after the phase-6 work that closed items 1–7 of
[the v1 readiness review](2026-07-09-v1-readiness.md). Scope this time:

1. Are the Python / Node / React / Go-Rust starter kits at **2026 standards**?
2. What **rot checks** (doc rot, test rot, drift) should exist, and which are traps?
3. Is this really the **minimal** base, or is there language/framework-specific
   weight that should come out?
4. Ship now, fix first, or keep building?

Method: every defect below was produced by *running* the tool — scaffolding throwaway
projects, running their own declared tasks, and building the Dockerfiles it generates.
Version claims were checked against PyPI, the npm registry, and endoflife.date on
2026-07-09, not from memory. Five research agents covered the ecosystem surface; where a
claim is theirs and I did not reproduce it myself, it is marked *(research, not reproduced)*.

---

## Summary

**The chassis got materially better and the scaffold output got materially worse than it
looks.** Phase 6 landed the registry, the CLI tests, the LICENSE, the schema-drift gate,
and a Windows CI matrix — 73 tests became 114, coverage is 96%, and every check is green.
None of that is in question.

But `initc init` still produces projects that fail their own declared checks, and this
time it is the Node path rather than the Python one. Three defects are reproducible in
under a minute each, and all three would be found by the first person who clones the repo
after reading a LinkedIn post about it.

**The three that block a release:**

| # | Defect | Proof |
|---|---|---|
| 1 | Every file `initc init` writes on Windows gets **CRLF** line endings. A fresh Node scaffold therefore fails its own `npm run lint` — 5 errors, before any code is written. | `write_text()` translates `\n` → `\r\n`; `biome check .` rejects all five emitted files |
| 2 | The generated Dockerfile runs `corepack enable`, **removed from Node ≥ 25**. `docker build` on a `node:26` stack dies. | `exit code: 127` on the `RUN corepack enable` layer |
| 3 | The **pip flavor installs no dev tools.** `pip install -e .` does not install PEP 735 `[dependency-groups]`, so a pip-flavor project scaffolds ruff/mypy/pytest into `pyproject.toml` and then omits them from the venv. `doctor` still says green, because its install check only asks whether `.venv/` exists. | `iniconfig ABSENT` after `pip install -e .`; present after `pip install --group dev` |

Three more that are real but less urgent: two stacks sharing a `root` **silently clobber**
each other's `.gitignore` (the Python one loses, so `.venv/` and `__pycache__/` stop being
ignored); the `.pre-commit-config.yaml` the tool scaffolds calls `initc`, which is **not on
PyPI and not in the scaffolded project's venv**, so the hook cannot run in any downstream
repo; and `package_manager` is a bare `str`, so the published JSON Schema gives editors no
enum for the one field most likely to be typo'd.

**Standards: mostly stale, in a way that is visible at a glance.** The Node preset pins
`typescript ^5.5.0` and `vitest ^3.0.0`. Those carets cannot reach TypeScript 7 (GA
2026-07-08) or Vitest 4 — a scaffolded project installs 5.9.3 and 3.2.7 on the day it is
created. The Python floors (`ruff>=0.5`, `mypy>=1.10`, `pytest>=8.0`) sit against current
0.15.21, 2.2.0, and 9.1.1. Nothing is *broken* by this; it simply reads as written in 2024.

**Tests folder: still does not need organizing.** Twelve flat files against sixteen source
modules, near 1:1, with a `conftest.py` that killed the duplication the last review flagged.
The slowest test is 1.9 s. Folders would be ceremony. `test_console_output.py` — an AST
walk asserting no non-ASCII string reaches a console — is the best file in the suite and
is exactly the kind of check §6 argues for more of.

**Docs: no longer wrong, still thin in one specific place.** The `--local` drift is gone,
every `initc <cmd>` mentioned in prose resolves to a real command, and zero relative links
are broken. The one gap that matters: **there is no way to install this tool.** Every doc
teaches `uv run initc …`, which only works inside this repo. For a tool whose pitch is
"clone *any* project," the missing distribution story is the largest documentation hole,
and it is what makes the scaffolded pre-commit hook dead on arrival.

**Is `framework:` the right axis? No.** Vendoring React presets makes this a worse,
permanently-stale clone of `create-vite`. In the last twelve months `@vitejs/plugin-react`
v6 dropped Babel, Vite 8 went Rolldown/ESM-only, React Router v8 went ESM-only, TypeScript
went native, and Tailwind v4 deleted its config file. A hand-vendored React preset would
have broken on every one of those. Stop at the language boundary; **describe** the
framework, delegate its creation to the framework's own creator.

**Is it the minimal base? Almost — the presets are the non-minimal part.** The durable core
is manifest + doctor + path-lint + env contract + task runner + beacons. None of that rots.
Everything that rots lives in the preset layer, which duplicates `uv init` (which already
emits `.python-version` and `py.typed`, both of which the preset omits) and re-litigates
tool opinions the design doc explicitly says the tool must not have.

**Rot checks: one pattern buys most of it.** Regenerate every committed artifact in CI and
`git diff --exit-code`. That single mechanism covers schema drift, CLI-doc drift, and
agent-file drift — three rot classes, one idiom, no new dependency. Then `uv sync --locked`
and `uv audit` (both native to the uv you already run). The traps are mutation testing in
CI, a global coverage `fail_under`, and docstring-coverage gates.

**Release: do not post today.** The correctness set is roughly half a day. The blocker
underneath it is distribution: `initc` cannot be installed into any project, which makes
the headline claim untestable by the audience most likely to test it. Fix the three
defects, make the package installable, then post. Detail in §8.

---

## 1. What changed since the v1 review

Seven of eight recommendations landed. The eighth was correctly deferred.

| v1 item | Status |
|---|---|
| 1. Scaffold `README.md`; add a real `initc init` round-trip test | Done — `test_cli.py`, incl. a real `uv sync` |
| 2. Root `.gitignore` independent of stack presets | Done, except the same-root clobber (§2.5) |
| 3. Add `LICENSE`; delete the `--local` claim | Done |
| 4. Scaffold `.pre-commit-config.yaml` + CI | Done — but the hook cannot run downstream (§2.6) |
| 5. Reconcile the two skills | Done — each now names the other |
| 6. Fix compose; per-stack `.dockerignore` | Done |
| 7. `LanguageProvider` registry + CI schema-drift gate | Done |
| 8. `framework:` axis | Deferred to ROADMAP — and §4 argues it should stay there permanently |

Tests 73 → 114. Coverage 96% (`cli.py` 92%, `doctor.py` 94%). CI gained a Windows matrix,
`--cov-fail-under=90`, and `initc schema && git diff --exit-code`. The v1 review doc
carries a "Status: adopted" banner fencing its now-historical findings, which is the right
way to keep a review honest after its fixes land.

The registry did what it was supposed to. `languages.py` is now the single place a language
is described, and `test_languages.py` asserts the registry and the manifest cannot disagree.
That refactor is the strongest thing in the repo.

---

## 2. Defects found by running the tool

### 2.1 CRLF: every scaffolded file, on Windows

`local_mode.write_missing` (and `env_contract`, and `cli.schema`) call
`path.write_text(content, encoding="utf-8")`. `Path.write_text` opens with `newline=None`,
which enables universal-newline translation *on write* — every `\n` becomes `os.linesep`.
On Windows that is `\r\n`.

```
os.linesep = '\r\n'
write_text("a\nb\n") -> b'a\r\nb\r\n'      # CRLF INJECTED
```

So a scaffold generated on Windows emits CRLF into `package.json`, `tsconfig.json`,
`biome.json`, `src/index.ts`, `tests/index.test.ts`, `.env.example`, `AGENTS.md`,
`Dockerfile`, and `compose.yaml`.

The consequence is §2.2. The fix is three characters times three call sites:
`write_text(content, encoding="utf-8", newline="\n")`.

**The repo already knew.** `ci.yml:29` reads *"regenerating on Windows rewrites the file
with CRLF and the diff is noise"* — and works around it by running the schema check on
Linux only. The symptom was diagnosed, the workaround was shipped, and the cause was never
touched. That pattern repeats below.

### 2.2 A fresh Node scaffold fails its own `npm run lint`

The Node preset emits a `lint` script (`biome check .`). Running it on a just-scaffolded
project, before writing a single line of code:

```
Checked 5 files in 20ms. No fixes applied.
Found 5 errors.
```

All five are CRLF formatting failures on the scaffolder's own output — `biome.json`,
`package.json`, `tsconfig.json`, `src/index.ts`, `tests/index.test.ts`. Biome's formatter
defaults to LF.

There is a **second, platform-independent** failure hiding behind it. After `npm run build`,
`biome check .` also lints `dist/`, because Biome does not read `.gitignore` unless
`vcs.useIgnoreFile: true` is set, and the emitted `biome.json` sets nothing:

```json
{ "linter": { "enabled": true }, "formatter": { "enabled": true, "indentStyle": "space" } }
```

So on Linux the first `lint` passes and the first `build && lint` fails. Two fixes: add a
`vcs` block (or a `files.includes` exclusion), and set `rootDir: "src"` — with
`rootDir: "."` and `include: ["src", "tests"]`, `tsc` compiles the tests into
`dist/tests/`, which is why the linted build output contains a test file.

For the record, the bare `{"linter": {"enabled": true}}` **does** lint: Biome 2.x enables
recommended rules by default *(research, reproduced in part — my run showed
`assist/source/organizeImports` firing on `dist/`)*. The config is thin, not inert.

### 2.3 The generated Dockerfile fails to build on Node ≥ 25

`NodeProvider.dockerfile_body` emits `RUN corepack enable` whenever the package manager is
pnpm. Corepack was removed from the Node distribution after 24.

```
node24: corepack PRESENT
node26: corepack ABSENT
```

Generating and building a `version: "26"` pnpm stack:

```
Dockerfile:4
   4 | >>> RUN corepack enable
ERROR: failed to solve: process "/bin/sh -c corepack enable"
       did not complete successfully: exit code: 127
```

The Python Dockerfile, by contrast, builds clean.

**The repo already knew this one too.** `NodeProvider.package_manager_fix` reads
*"corepack enable (Node >= 25 ships without corepack: npm install -g corepack first)"* —
the doctor's fix string carries the fact, and the Dockerfile generator two methods away
ignores it. Same shape as §2.1: knowledge recorded in one place, not propagated to the
other.

Fix: drop corepack and `RUN npm i -g pnpm@<version>`, or gate the corepack line on
`int(stack.version.split(".")[0]) < 25`. Note also that `RUN pnpm install` should be
`pnpm install --frozen-lockfile`, and the `COPY pnpm-lock.yaml*` glob quietly tolerates a
missing lockfile — an unpinned install in an image that exists to be reproducible.

### 2.4 The pip flavor installs none of the dev tools it declares

`PythonProvider.install_steps` runs `pip install -e .` for a pip stack. PEP 735
`[dependency-groups]` are **not** installed by installing the project. Verified against
pip 26.1.2, using the preset's own pyproject shape with a canary dependency in the dev
group:

```
pip install -e .        -> iniconfig ABSENT   (dev group not installed)
pip install --group dev -> Would install iniconfig-2.3.0
```

So a pip-flavor scaffold declares `mypy`, `pytest`, and `ruff` and then ships a venv
without them. `initc run test` fails with `pytest: command not found`.

`doctor` reports this as healthy, because `_install_dir_check` asks only whether `.venv/`
is a directory. That check answers "did *something* run," not "is this checkout ready."
The same weakness is what makes Go impossible to model (§3.4).

Fix: append `pip install --group dev` to the pip install steps. Fix the check too: proving
the environment works means invoking something from it.

### 2.5 Two stacks at the same root silently clobber each other

The manifest enforces unique stack *names*, never unique *roots*. A python stack and a node
stack both rooted at `.` validate cleanly, and then `plan_files` builds a dict keyed by
path — so the second stack's `.gitignore` overwrites the first's, before anything touches
disk:

```
manifest VALIDATED with two stacks at the same root
.gitignore starts with: '# Dependencies live INSIDE the project b'   <- node's
```

The Python ignore file is gone: `.venv/`, `__pycache__/`, `*.py[cod]`, `.pytest_cache/`,
`.mypy_cache/`, `.ruff_cache/`, and `.coverage` are no longer ignored. `.env` survives only
by coincidence, because the Node template happens to list it too. `README.md` and `tests/`
collide the same way.

Fix: either reject duplicate roots in the model validator (cheapest, and consistent with
how the tool already teaches through validation errors), or merge same-root `.gitignore`
files. Silently taking the last writer is the one option that should not stand.

### 2.6 The scaffolded pre-commit hook cannot run in any downstream repo

`presets/common.py` writes this into every project:

```yaml
      - id: lint-paths
        entry: initc lint-paths
        language: system
```

`language: system` means "this binary is already on PATH."

```
initc ABSENT from the scaffolded project's own .venv
PyPI init-configurator -> HTTP 404
initc: not on global PATH
```

So the hook fails for every downstream user, and the project's own rule — *no global
installs* — forbids the one workaround. Meanwhile `.pre-commit-hooks.yaml`, which ships in
this repo and *is* the mechanism that would work (pre-commit clones the repo and installs
it into an isolated env), points at `<this repo's URL once published>` and is never used
by the generator.

This is the distribution gap wearing a different hat. Until `initc` is installable, the
honest options are to emit the hook commented out with a one-line explanation, or to emit
the `repo:`/`rev:` form pointing at the published repo and not scaffold it until that
exists.

Note also that the scaffolded hook omits `types: [text]`, which this repo's own config sets
— so downstream, `lint-paths` gets handed binary files. `scan_file` swallows the
`UnicodeDecodeError`, so it is slow rather than broken.

### 2.7 The doctor's version contract does not survive a compiled language

Not a live bug — `python` and `node` both accept `--version` — but it is the wall the
registry hits the moment a third language is added, and it is worth knowing before
promising Go support.

`_binary_version` runs `<binary> --version` and reads **stdout**. Verified inside
`golang:1.26`:

```
go version              -> "go version go1.26.5 linux/amd64"   (stdout)
go --version            -> stdout=[]  exit=2
                           stderr: flag provided but not defined: -version
```

Go's version is a subcommand, not a flag. `_binary_version("go")` returns `None`, and
doctor reports **"'go' not found on PATH"** on a machine where Go is installed correctly.
Because a Go stack's `package_manager` is also `go`, both the runtime check and the
package-manager check fail together.

The regex is fine — it extracts `1.26.5` from the real `go version` output. The *matcher*
is the deeper problem:

```
declared=3.12  installed=3.12.5  -> True     # Python: pin the minor. Correct.
declared=1.24  installed=1.26.5  -> False    # Go: `go 1.24` is a MINIMUM. Wrong.
declared=1.85  installed=1.97.0  -> False    # Rust rust-version is an MSRV. Wrong.
```

`_version_matches` is prefix-equality. Go's `go` directive and Rust's `rust-version` are
*floors*: a newer toolchain is correct, and the doctor would fail it.

`install_dir` is the third wall. Go has no in-project dependency directory at all — modules
land in a global, content-addressed, checksum-verified module cache, and that is idiomatic,
not a smell. Rust's `target/` is build output, not dependencies. **The "no global installs"
rule is a Python/Node-shaped rule that does not generalize**, and `install_dir: str` cannot
express it.

And a trap worth naming: `dependency_files` has `min_length=1`, and the scaffolder *creates
any declared dependency file that does not exist*. A Go provider that declared `go.sum` to
satisfy `_dependency_file_checks` would emit a hand-written checksum file, and Go treats a
bad `go.sum` hash as `SECURITY ERROR`. The only safe declaration is `["go.mod"]` /
`["Cargo.toml"]`, with the lockfile generated by the toolchain. *(research; the failure
modes are documented Go/Cargo behavior, not reproduced here.)*

Finally, `docker_mode._cmd_line` always appends `CMD ["sh","-c","<task>"]`. A Go image's
CMD is a compiled binary in a distroless final stage. Following the current model would
bake the Go toolchain into the runtime image and recompile on every container start.

**Conclusion:** adding Go is not "one object." It is `install_dir: str | None` (or a
`verify_installed()` predicate), a provider-owned version command, minimum-version
semantics, and provider-owned Dockerfile/CMD. Roughly eight changes across four modules
before `GoProvider()` becomes a one-liner. Either do that, or say in the README that the
Protocol targets interpreted, per-project-dependency languages — which reads as
self-awareness, not as a limitation.

### 2.8 The published schema under-delivers on its promise

The README says the JSON Schema *"gives editors autocomplete and inline validation."*

```
language           -> {"enum": ["python", "node"], "type": "string"}
package_manager    -> {"type": "string"}
version            -> {"type": "string"}
```

`language` has an enum. `package_manager` does not, because it is declared `str` and
validated in a model validator. So an editor autocompletes nothing and happily accepts
`package_manager: npm` on a python stack — the exact mistake the teaching error was written
for. The validator is correct; the *schema* is where a user finds out early.

---

## 3. Standards currency, mid-2026

All versions pulled from PyPI / npm / endoflife.date on 2026-07-09.

### 3.1 Python — structurally right, numerically stale

| | Preset floor | Current | |
|---|---|---|---|
| ruff | `>=0.5` | **0.15.21** | ~10 minors behind |
| mypy | `>=1.10` | **2.2.0** | a major behind |
| pytest | `>=8.0` | **9.1.1** | a major behind |
| uv | `:latest` (Docker) | 0.11.28 | unpinned — see below |

The *shape* is 2026-correct: PEP 735 `[dependency-groups]` is the right table (uv ≥ 0.4.27,
pip ≥ 25.1), `[tool.ruff.lint] select` is the right key, `strict = true` is the right mypy
posture, and the absence of a `requires-python` upper bound is right. The floors just read
as 2024.

Three concrete items beyond the floors:

- **`COPY --from=ghcr.io/astral-sh/uv:latest`** is against Astral's documented practice —
  pin a version or a digest. `:latest` means every rebuild may pull a different uv. On a
  repo whose pitch is reproducibility, this is the most quotable line in the codebase.
- **`uv sync` in the Dockerfile is not `--locked`.** Combined with the optional
  `COPY … uv.lock*` glob, an image with no lockfile resolves dependencies fresh at build
  time. I built one; it succeeded, which is the problem.
- **`target-version` is redundant** now that ruff infers it from `requires-python`
  (since ruff 0.10), and it is derived from the user's Python version, so a `3.15` stack
  would emit `target-version = "py315"`, which ruff does not accept. *(research; latent,
  not currently reachable.)*

Missing and cheap: `uv.lock` committed, `.python-version`, `py.typed`. `uv init --lib`
emits the last two for free (see §5). Type-checker landscape: mypy remains the defensible
default; pyrefly reached 1.0 in May 2026 and `ty` is still 0.0.x beta *(research)*.

### 3.2 Node — two shipped defects and a version cap

Covered in §2.2 and §2.3. The remaining issue is the caret floors:

| | Preset pin | Resolves to | Current |
|---|---|---|---|
| typescript | `^5.5.0` | **5.9.3** | **7.0.2** |
| vitest | `^3.0.0` | **3.2.7** | **4.1.10** |
| @biomejs/biome | `^2.0.0` | 2.5.3 | 2.5.3 |
| @tsconfig/strictest | `^2.0.0` | 2.0.8 | 2.0.8 |

`^5.5.0` means `>=5.5.0 <6.0.0`. A project scaffolded today **cannot** install TypeScript 7
(GA 2026-07-08, the Go-native compiler) or Vitest 4. The two carets that matter are the two
that are capped.

Node itself: 24 is Active LTS, 26 is Current and promotes 2026-10-28, 22 is Maintenance, 20
is EOL. `engines.node: ">=24"` is the right default and is what the preset emits — the
design doc's "revisit Oct 2026" note is accurate.

Also missing: a `typecheck` script. The manifest models a `typecheck` task, and
`package.json` has `build: tsc` (which emits) but no `tsc --noEmit`. A Node stack declaring
`typecheck` has nothing to run.

`@tsconfig/strictest` already sets `isolatedModules` and `noUncheckedIndexedAccess`. It does
*not* set `verbatimModuleSyntax` or `erasableSyntaxOnly`, the two flags that keep `tsc` and
Node's native type-stripping in agreement *(research)*.

### 3.3 React — a preset here would already be broken

React 19.2.7, Vite 8.1.4, React Compiler 1.0 stable. `create-react-app` was deprecated
2025-02-14; react.dev now recommends starting with a framework, and names Vite/Parcel/Rsbuild
for from-scratch builds *(research)*.

In the last twelve months: `@vitejs/plugin-react` v6 dropped Babel for oxc (so every 2025
"enable React Compiler in Vite" recipe silently no-ops), Vite 8 went Rolldown and ESM-only,
React Router v8 went ESM-only and Node 22+, TypeScript went native, Tailwind v4 deleted
`tailwind.config.js`. A vendored React preset written six months ago would be wrong on all
five counts today. See §4.

### 3.4 Go and Rust — the abstraction, not the versions, is the blocker

Go 1.26.5 stable, two supported majors (1.26, 1.25). Rust 1.97.0, edition 2024. Neither is
hard to look up. The blocker is §2.7: `install_dir`, the version command, minimum-version
semantics, and the CMD contract all assume an interpreted language with a per-project
dependency directory.

A shallow Go provider would report "go not found" on every machine with Go installed. On a
repo where code quality is the product, that is the most expensive possible bug — a
reviewer who knows Go finds it in thirty seconds.

---

## 4. Is `framework:` the right axis? No.

Three designs:

| | Design | Who owns freshness | Verdict |
|---|---|---|---|
| a | `framework: react` → presets vendored in this tool | **You** | Reject |
| b | No framework field; the manifest *describes* what the user scaffolded | Framework teams | **Default** |
| c | A `create:` field that shells out to the framework's own creator | Framework teams | Optional escape hatch |

The argument is one sentence: **a vendored Next.js template is stale in six months;
`create-next-app` never is**, because the freshness obligation lives with the team that
ships it. Design (a) moves that obligation onto a solo maintainer, against five
simultaneously-moving upstreams (§3.3).

Yeoman is the cautionary tale — it faded precisely because maintaining generators is
unwinnable. Nx vendors generators and pays a full-time team to do it. `degit`, `copier`,
and `npm create` all keep templates outside the tool. react.dev itself links straight to
`npx create-next-app@latest`.

The honest ceiling: the moment the tool emits a `vite.config.ts`, an `index.html`, or an
`App.tsx`, it has crossed from *language baseline* into *framework baseline*, and a React
project's essence — routing, SSR, data, styling, compiler wiring — is entirely framework
baseline. So the tool cannot generate "a React project" without becoming a framework
scaffolder.

What it *can* do, and already does, is framework-agnostic and durable: `package.json`
scripts, a strict tsconfig, lint/format, a test runner, a Dockerfile, the env contract, and
the task map. **Keep the ROADMAP entry deferred, and change its framing** from "the next
real feature" to "deliberately out of scope, here is why." That framing is a stronger
portfolio signal than the feature would be.

---

## 5. Is this the minimal base?

The core is minimal and durable. The preset layer is neither.

**Durable (does not rot):** the manifest and its teaching errors; `doctor`'s three-state
model; path-lint and `project_root()`/`path_to()`; the `.env` contract and its drift diff;
the task runner; the beacon/discovery chain. None of these encode a version number or a
tool opinion. This is the actual product.

**Rots (every one of §2.2, §2.3, §3.1, §3.2 lives here):** `python_preset.PYPROJECT_TEMPLATE`
and `node_preset` — a ruff rule selection, `line-length = 100`, mypy strict, a Biome config,
a tsconfig, five pinned devDependencies.

Two things follow.

**First, the presets contradict the design doc's own rule.** `manifest-v1.md` says *"Nothing
stack- or project-specific ships as a default"* and *"the manifest stays ignorant of tool
configs."* But the Python preset ships `select = ["E","F","I","B","UP","SIM","N","RUF"]`
and `line-length = 100` — Stepan's opinions, hard-coded into every downstream project.
That is not a bug; it is an unstated policy. Either state it (*"the preset is opinionated on
purpose; here is the opinion"*) or thin it.

**Second, upstream already does most of this, better.** `uv init --lib` emits:

```
.gitignore  .python-version  README.md  pyproject.toml  src/<pkg>/__init__.py  src/<pkg>/py.typed
```

That is a superset of the Python preset's structural output, *plus* the two files the
research flagged as missing. It will never be stale, because Astral maintains it.

**What to remove or thin:**

- Delegate structure to `uv init` where it exists; keep only the manifest-derived layer on
  top. The same argument points at `npm create` for Node.
- Drop `target-version` (ruff infers it) — one less thing to get wrong.
- Consider moving the ruff rule selection and `line-length` behind a documented "opinionated
  defaults" flag rather than an unmarked default.
- The `.pre-commit-config.yaml` should not be scaffolded until the hook it references can
  actually run (§2.6).

What should **not** be removed: the beacons. Three files (`AGENTS.md`, `CLAUDE.md`, the
instantiated skill) that make a cloned repo legible to a coding agent are the most
differentiated thing here, and nothing upstream does it.

---

## 6. Rot checks

### The one pattern that matters

Every committed artifact that is *generated* should be regenerated in CI and diffed:

```bash
uv run initc schema && git diff --exit-code schema/
```

This already exists for the schema. Extend it to two more artifacts and it covers three rot
classes with one idiom and zero new dependencies:

- **CLI reference.** Verified working today:
  `uv run typer init_configurator.cli utils docs --name initc --output docs/cli.md`
  This is the direct antidote to the `--local` failure — a documented-but-nonexistent flag
  cannot survive a diff against the live Typer app.
- **Agent context files.** The repo *generates* `AGENTS.md`/`CLAUDE.md`/`SKILL.md` for
  downstream projects. Nothing keeps this repo's own copies honest. Regenerate and diff.
  Note: there is currently **no `initc beacons` command** — one of the research agents wrote
  a config snippet assuming there was. Writing it is a prerequisite, not a detail.

Complement it with a ~20-line test that extracts every backtick-quoted `` `initc <cmd>` ``
from the markdown and asserts it resolves against `app.registered_commands`. That catches a
lie in a *hand-edited* file, which a diff cannot. `test_console_output.py` already proves
this style of invariant test works here.

### Worth adding, ranked by value over noise

| Check | Why | Cost |
|---|---|---|
| Generate-and-diff (schema, CLI docs, beacons) | Kills 3 rot classes; ~zero false positives | ~15 lines |
| `uv sync --locked` in CI | Stale lockfile. **Verified: exists, passes today** | 1 line |
| `uv audit` in CI | Known-vuln deps. **Verified: exists** | 1 line |
| `pytest-randomly` (4.1.0) | Order-dependent tests — nothing else catches these | 1 dev-dep |
| `check-jsonschema` | Validates `project.yaml` against the shipped schema, and the workflow/pre-commit YAML against theirs | 1 hook |
| EOL check via endoflife.date | Fails when `requires-python`'s floor goes EOL. Distinctive, near-zero noise | ~10 lines |
| `diff-cover` (10.3.0) on PRs | Patch coverage instead of a global threshold | 1 dev-dep |
| `lychee` link check | **On a weekly cron, never on push** | 1 workflow |

Coverage note: CI already runs `pytest --cov --cov-fail-under=90`, so the v1 finding
("coverage never runs") is **resolved** — but `initc run test` is `uv run pytest`, so the
local task and the CI gate are not the same command. Worth aligning, or worth a comment
saying why not.

### Traps — do not add

- **Mutation testing in CI.** `mutmut` 3.6.0 is alive and much faster, but it is a
  minutes-to-hours, non-deterministic job. Chronically red → disabled. Run it once, put the
  surviving-mutant count in a comment, move on.
- **A global coverage `fail_under`.** Rewards tests that touch lines without asserting.
  `diff-cover` on changed lines is the honest gate. (The current 90% global gate is mild,
  but it is the shape that goes wrong as the repo grows.)
- **`interrogate`.** Measures docstring *presence*, not truth. Theater.
- **`pydoclint` / ruff `DOC` param rules.** Correct in principle — `pydoclint` 0.9.1 is the
  only real "docstring params match the signature" tool, and ruff's `DOC101` is not shipped
  stable — but on Typer command signatures it fires relentlessly and gets `# noqa`'d into
  irrelevance.
- **`darglint`.** **Verified archived** (`archived=True`, last push 2022-12-08). Do not adopt.
- **An AGENTS.md linter.** The three that exist (`ctxlint`, `agents-lint`, `agentlint`) are
  single-maintainer, 7–11 star, Node-centric tools that check `package.json` scripts. They
  cannot verify `initc run test` resolves in a Typer app. Generate-and-diff is more reliable
  and has no dependency. *(research)*

### The rot this repo has right now

A doc-rot check would earn its keep on day one: `docs/design/manifest-v1.md` has **five code
fences** — an unbalanced, stray ``` at EOF. Nothing in CI or pre-commit inspects markdown at
all; `path-lint` reads `**/*.md` but only for absolute paths. (Relative links, at least, are
all live: 0 broken.)

---

## 7. Skills

The instinct — "add skills for Python standards, FastAPI, React standards, Go standards,
testing standards" — would reproduce the preset problem in a place where **no CI can see it.**
A skill that says `typescript ^5.5.0` rots exactly like the preset that says it, except
nothing fails when it does. An agent then reads the stale skill and confidently writes 2024
code.

The distinction that survives:

- **Skills that encode version numbers rot.** "Pin TypeScript ^5.5."
- **Skills that encode decision procedures do not.** "Before pinning any dependency, check
  the registry (`npm view <pkg> version`); never write a caret that cannot reach the current
  major; a caret is a ceiling, not a floor."

Every research agent in this review was told to verify against a live registry rather than
recall, and that instruction is what made the findings trustworthy. That instruction is the
skill.

**Worth writing:**

1. **`add-a-language`** — the registry contract, and the four places it leaks for compiled
   languages (§2.7). This is repo knowledge that exists nowhere else and cannot rot.
2. **`verify-before-pinning`** — the decision procedure above. One page. Would have prevented
   §3.1 and §3.2 outright.
3. **`rot-check`** — the generate-and-diff idiom, and the list of artifacts subject to it.

**Not worth writing:** "React standards 2026," "FastAPI standards," "Go standards." They are
a snapshot with a six-month half-life, they duplicate what an agent can look up on demand,
and — per §4 — the framework layer is deliberately not this tool's job. If a React skill is
wanted, its entire content should be: *run the official creator; then write a `project.yaml`
that describes the result.*

---

## 8. Release decision

**Do not post today. Fix, publish, post tomorrow.**

The reasoning, not the ceremony:

A LinkedIn post about a project scaffolder is read by people who scaffold projects. A
meaningful fraction will clone it and run it — that is the *entire* audience. Today they hit
one of three things within a minute: a Node scaffold that fails its own lint, a Dockerfile
that will not build, or a pip project with no test runner. The README's first line is
*"Clone any project. Run one command. It works."* Right now, for the Node path, it does not,
and the claim is checked at exactly the moment it is made.

Underneath the defects is a harder blocker: **`initc` cannot be installed.** Not on PyPI, not
in a scaffolded project's venv, and the project's own "no global installs" rule forbids the
workaround. A tool that configures *any* project cannot currently be added to *any* project.
The scaffolded pre-commit hook is the visible symptom; the missing distribution story is the
disease. This is a publish blocker in the literal sense.

Costed:

| | Work |
|---|---|
| **Before posting** | `newline="\n"` (3 sites) · corepack guard · `pip install --group dev` · Biome `vcs` block + `rootDir: "src"` · duplicate-root validation · bump the caret floors and Python floors · pin the uv image, add `--locked` · publish the package (or `pip install git+…` documented, with `.pre-commit-hooks.yaml` wired to the real URL) |
| **Same day, cheap** | `typecheck` script in `package.json` · `package_manager` as a per-language `Literal` so the schema gets an enum · fix the stray code fence |
| **Next** | Generate-and-diff for CLI docs and beacons · `uv sync --locked` + `uv audit` · `pytest-randomly` |
| **Later / never** | `framework:` (never — §4) · Go/Rust (only with the eight changes in §2.7) |

That is most of a day, not a week. The correctness set is small because the architecture is
good — the registry means the corepack fix is one method, and the CRLF fix is one keyword
argument in three places.

**And post about the right thing.** The scaffolder is not the interesting artifact; there are
many. The interesting artifact is `docs/reviews/` — a public repo that reviews itself
adversarially, writes down what it found, fixes seven of eight items, and keeps the record of
why. Very few portfolio repos contain a document that says "the headline command was broken
and here is the A/B test that proved it." That is the senior signal, and it is already
written. The one thing that would undercut it is shipping a fourth defect of the same class
on the same day.

---

## How this was verified

Reproduced directly in this session: the CRLF byte-level injection; `npm run lint` failing on
a fresh Node scaffold (5 errors) and again on `dist/` after build; `docker build` exiting 127
on `corepack enable` for `node:26-slim`, with `node:24-slim` as a passing control; the Python
Dockerfile building clean; `pip install -e .` omitting the dev group under pip 26.1.2, and
`pip install --group dev` installing it; the same-root `.gitignore` clobber via `plan_files`;
`initc` absent from a scaffolded venv and PyPI returning 404; `go --version` returning empty
stdout and exit 2 inside `golang:1.26`, while `go version` prints `go1.26.5`;
`_version_matches("1.24", "1.26.5") == False`; the schema's missing `package_manager` enum;
`uv audit`, `uv lock --check`, and `uv sync --locked` all existing and passing; the correct
`typer … utils docs` invocation; `initc beacons` **not** existing; the unbalanced code fence;
zero broken relative links; 114 tests at 96% coverage; a scaffolded Python project passing its
own `test`, `lint`, and `typecheck`.

Version numbers from PyPI, the npm registry, and endoflife.date on 2026-07-09. `darglint`'s
archived status from the GitHub API. Items marked *(research)* come from the five research
agents and were not independently reproduced here.
