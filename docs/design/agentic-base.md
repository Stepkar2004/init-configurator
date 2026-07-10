# The agentic base — what this project actually is

> Written 2026-07-09, after stopping phase 7 mid-implementation. This supersedes the
> generation half of [manifest-v1.md](manifest-v1.md); the verification half of that
> document still stands. The two reviews in [docs/reviews/](../reviews/) are the evidence
> that led here and remain accurate as history.

## Why we stopped

`initc init` on an empty folder wrote a `pyproject.toml` carrying one person's ruff rules,
a `biome.json`, two tsconfigs, five pinned devDependencies, and a Dockerfile. Adding a
language meant writing — and then forever maintaining — a folder of file contents. That is
`create-vite` with a single maintainer, and it is not what this project was for.

The evidence was already in the repo before anyone said it out loud. Across two adversarial
reviews, **every defect found lived in the generation layer**: CRLF in written files, a
Dockerfile calling `corepack enable` on a Node that removed it, a `typescript ^5.5.0` caret
that could not reach the current major, a pip flavor that installed none of the dev tools it
declared. **Not one defect lived in the verification layer** — `doctor`, `path_lint`,
`env_contract`, `runner`, `manifest`. The second review said it in a sentence — *"The core is
minimal and durable. The preset layer is neither"* — and the response was to spend a day
hardening the preset layer.

There was a second, quieter failure. The knowledge was stored where only the tool could
reach it. `PYPROJECT_TEMPLATE` is a Python string constant: an agent working in a cloned repo
cannot read it, cannot reason about it, cannot adapt it to a project that is already
half-built. A tool that exists to make repos legible to agents had put its own knowledge
somewhere no agent would ever look.

## The line

**Skills know _how_. Tools know _whether_. `project.yaml` records _what_.**

Generation is a knowledge problem. It must be current, it differs per project, and it is done
far better by a model that can query npm today than by a template frozen last year. It belongs
to the agent, guided by skills.

Verification is a determinism problem. It must run on every commit with no agent present, and
it must answer yes or no. It belongs to a script.

The old design put generation in the tool. That is the whole bug, and everything else follows
from it.

### What this buys

Three properties the template design could not have:

- **Scales to many languages.** A runtime is defined by how you *check* it, not by the files
  you *write* for it. Adding Go is a small data object plus a reference file — not a preset
  folder with a shelf life.
- **Upgrades itself.** Standards live in markdown an agent reads and edits. The 2029 version of
  `references/python.md` is written by whoever is working in 2029, not by us today.
- **Grounds the agent.** The agent is subject to the same exit codes as a human. It cannot
  argue with a failing pre-commit hook. The gates were always the grounding; the templates
  never were.

## The problems this solves, and the mechanism for each

Each row is a real pain point. The middle column is what handles it. Note how much of it already
exists — the pivot deletes far less than it keeps.

| Pain | Mechanism | State |
|---|---|---|
| The agent forgets where `.venv` / `node_modules` / the data dir live | `project.yaml` declares them; the beacons make the agent read it; `doctor` verifies them | built |
| Absolute paths land in code and break every other clone | `path-lint` + the pre-commit hook + `project_root()` / `path_to()` helpers | built |
| An env var is needed, no template exists, you hunt for the name | Declare in `project.yaml` → `initc env` writes `.env.example` → doctor's `env-sync` fails on drift, both directions | built; needs the *skill rule*: declare and regenerate in the same turn the code first reads the var |
| Duplicate and low-quality code accumulates; human review is the bottleneck | Deterministic opt-in tools, offered as a menu at phase 0 and enforced by hooks: `jscpd` (copy-paste), `knip`, `dependency-cruiser`, `vulture`, `radon` | belongs in `references/quality-tools.md` — **a menu, never a default** |
| Unwanted tools get forced on the project | Phase-0 interview. The *choice* lands in `project.yaml` (machine-checkable); the *reason* lands in the skill (agent-readable next session) | new |
| Naming, docstring, and test standards drift | They are linter config (ruff `N`, `D`; pytest conventions). Written once from your answers, enforced forever by the linter | interview output, not a template |
| A tool stops earning its keep; a class of bug keeps recurring; a refactor procedure is missing | The skill evolves. A lesson is appended as a *procedure*, reviewed as a diff | new — see below |

## Phase 0, as a transcript

The spec, by example. This is the thing to build.

> **You:** "New project: a CLI that tracks my climbing sessions. Python."
>
> **Agent** *(the `bootstrap` skill triggers; it reads `references/python.md`)*:
> Three questions. uv or pip? Quality tools — ruff and mypy are the baseline; the opt-in menu
> is vulture for dead code, jscpd for copy-paste, radon for complexity. Docs — a mirrored
> `docs/` tree, or README-only?
>
> **You answer.** The agent runs `uv init --lib` — the *real* creator, kept current by Astral,
> not by us — then builds the `src/` `tests/` `docs/` mirror, wires pre-commit with exactly the
> tools you chose, and writes `project.yaml` describing all of it.
>
> **The gate:** `initc doctor` is green. `initc run test` passes on the empty project.
> `initc lint-paths` is clean. First commit made. Phase 0 is done, and it is *provably* done.
>
> **Three weeks later** your code reads `STRAVA_API_KEY`. The base skill's rule made the agent
> declare it in `project.yaml` and regenerate `.env.example` in the same turn. Had it forgotten,
> `env-sync` fails the next `doctor`. You never hunt for a variable name again.
>
> **A month in** you decide `ty` beats mypy here. You say so. The agent updates `project.yaml`
> and edits `references/python.md`: *"consider ty when X — checked 2026-08."* You approve the
> diff. Your next project inherits the lesson.

## The stages, and what governs each

Every stage has a skill (how), a gate (whether), and an artifact (what persists).

| # | Stage | Skill | Gate | Artifact |
|---|---|---|---|---|
| 0 | Frame | — | human | a brief |
| 1 | Shape | `bootstrap` (interview) | `initc validate` | `project.yaml`, ADRs |
| 2 | Ground | `bootstrap` + `references/<stack>.md` | `doctor` green, `run test` passes | a working tree |
| 3 | Contract | `project-base` | `env-sync` | `.env.example`, failing tests |
| 4 | Build | stack references | tests, types, lint | code |
| 5 | Verify | `rot-check` | CI | `docs/reviews/` |
| 6 | Ship | — | generate-and-diff | a release |
| 7 | Operate | — | — | — |
| 8 | Evolve | `evolve`, `skill-manager` | approved diff | edited skills |

The old design addressed stage 2 alone, and addressed it by freezing templates — the single
strategy guaranteed to fail stage 8.

## Skills: how the loading actually works

Not a metaphor; this is the mechanism.

1. **Metadata** — every skill's name and description sit in context permanently, about a line
   each. This is the always-resident index of what the agent knows how to do.
2. **Body** — `SKILL.md` loads only when the skill triggers. Keep under ~500 lines.
3. **Resources** — `references/*.md` and `scripts/*` load only when the body points at them.
   Unbounded, because they cost nothing until read.

So `bootstrap/SKILL.md` holds the procedure that never changes, and `references/python.md`
holds the per-stack knowledge that changes constantly. The agent reads one reference file, not
all of them. **Adding Rust is adding `references/rust.md`.**

Models are known to *under*-trigger skills. Two mitigations, both used here: descriptions are
written to be pushy and specific about when to fire, and `CLAUDE.md` — the one file always
loaded in full — instructs the agent to consult the skill index before acting.

### The rule that keeps skills from rotting

**Skills that encode version numbers rot. Skills that encode decision procedures do not.**

`ruff>=0.15` is false in nine months and no CI can see it go stale — an agent then reads the
skill and confidently writes stale code. Instead: *"before writing any version constraint, query
the registry (`npm view <pkg> version`, the PyPI JSON API, endoflife.date); a caret is a ceiling
as well as a floor, so one that cannot reach the current major is stale on arrival; pin container
images; record the date you checked."* That sentence is still true in 2029.

Everything learned while hardening the preset layer moves here, unchanged in substance:
corepack is gone from Node ≥ 25 and `RUN corepack enable` exits 127; `pip install -e .` does not
install PEP 735 dependency-groups; `Path.write_text` translates newlines to `os.linesep`;
`uv init --lib` already emits `.python-version` and `py.typed`; `go --version` does not exist —
it is `go version`, a subcommand, and Go's declared version is a floor, not a pin. None of that
is wasted. It stops being Python constants and becomes knowledge an agent can read.

### Skill hygiene: the manager

Self-evolution becomes self-entrenchment without rules. These are load-bearing, and they
belong to one skill with global awareness of all the others — `skill-manager`:

- **A skill edit is a code change.** It goes through a diff a human approves. An agent that can
  silently rewrite its own instructions will fossilize its own mistakes, and no test will fail.
- **Skills exist per task-shape, never per incident.** A recurring bug becomes one appended
  procedure in an existing skill, not a new skill. Variants of one shape are `references/`
  inside one skill (`bootstrap` + `references/python.md`), never sibling skills
  (`bootstrap-python`, `bootstrap-react`). This is the abstraction-altitude call, and the
  smells for getting it wrong are inherited from TheBrain2's tree-method: **the same diff
  recurs after a fix → you patched too low; one edit forces rewriting siblings → too high.**
- **Lessons are procedures, not anecdotes.** *"Generated files are written LF explicitly, because
  `write_text` translates newlines"* — not *"fixed the CRLF bug on Jul 9."* The first is applied;
  the second is skimmed.
- **A miss-log.** When a task matches no skill, that is an event worth one logged line — it is
  the system noticing a gap in itself. Without it, the agent free-styles the same gap forever
  and nobody ever knows.
- **A periodic pass** asks: has this skill fired in the last N sessions? does any line encode a
  version number? is one skill doing two stages' work, or two skills doing one stage's? are
  there miss-log entries that have earned a new skill? A bloated skill fails silently — it
  simply stops being read carefully. The manager sets its own thresholds and adjusts them —
  through the same reviewed-diff door as everything else.

## The genome model

Projects stay **detached**. This is open source: nothing may assume that a stranger's clone
syncs with anything of ours. But detached does not have to mean isolated.

The behaviour we want is bacterial, and the analogy is exact enough to design against:

- **The genome** is the skill set, the standards, the gates, and `project.yaml`.
- **Division (vertical inheritance).** An init project that has evolved good genes can spawn a new
  init project carrying its current genome. `initc spawn ../new-project`.
- **Conjugation (horizontal transfer).** An init project can absorb genes from *any* repo — one
  that was never an init project included. `initc absorb ../some-repo` proposes the skills and
  standards it found, as a reviewable diff.
- **Selection pressure.** The gates. A gene that cannot pass `doctor`, `lint-paths`, and the test
  suite does not survive in the host.
- **Immunity.** Human review of every skill diff. Horizontal transfer is exactly how a bad gene
  gets in; the diff is the membrane.

`initc describe` — read an existing repo and write the `project.yaml` that describes it — is the
first half of conjugation, and it is also the command that was never built. It is what "adapts to
any project" actually means. The old design assumed the folder was empty.

# Part II — the system, generalized

> Added the same day, after the scope conversation widened. Part I above is the software-project
> base. This part records the anatomy of the larger system that base is the seed of — a system
> meant to evolve to meet any task at any stage — and, honestly, where it will still break.
>
> **Lineage.** The theory is TheBrain2's kernel (`knowledge/system/fundamental.md`):
> intelligence = speed of adaptation; adaptation = detect a diff with reality × edit cheaply;
> the two atomic acts are **attention** and **trust**. Idea trees are skills. The problems log
> is lesson capture. `/review` is the manager. The status ladder is the trust model. This base
> is that kernel compiled into an executable substrate — and code is the one domain where the
> reality-diff arrives *free*, as an exit code. TheBrain2 had to build rubrics to get feedback;
> a repo gets it from pytest. Same organism, faster selection pressure.

## The organs (drop one and the system dies a known death)

| Organ | Role | Dies without it as |
|---|---|---|
| **Constitution** (`CLAUDE.md`) | How to think and behave — never how to do a task. Thin, always loaded in full, points at everything else | values re-improvised every session |
| **Vision** (`docs/vision.md`) | The human-owned WHY. Only the human edits it. Everything downstream derives from it | fast, confident optimization toward the wrong target |
| **Skills** (`.claude/skills/`) | How to do each recurring task-shape: gather, dissect, execute, verify, validate. Variants live in `references/`, lazy-loaded | every session starts dumb; solved problems get re-solved |
| **Tools** (`src/`, hooks, CI) | Deterministic delegation — *whether*, never *how*. Model-free, cheap, un-arguable. Everything the system decided to enforce on itself, remembered as code | quality gated on model self-report; tokens burned on checks a script does for free |
| **State** (`docs/state/`) | Where we are, what is next, what happened — written every chunk, committed with it | a cut session loses the plot; resumability by archaeology |
| **Trust ladder** | Every learned claim carries `raw → active → validated → stale`. Agent-inferred = raw. Only the human promotes. Validated claims are stood on without re-checking; raw ones re-verified before anything is built on them | the system entrenches its own unverified guesses — self-evolution's worst failure |
| **Skill-manager** | Global awareness of all skills: consolidation altitude, self-set thresholds, the miss-log, decay of stale content | sprawl (a thousand near-duplicate skills) or blindness (the same gap free-styled forever) |
| **Fresh-eyes review** | The writer never grades its own work (TheBrain2 Law 7). Graders and reviewers get clean context | degradation invisible from inside; plausible-but-wrong survives its author's optimism |
| **Conjugation** (`spawn` / `absorb`) | Vertical inheritance and horizontal transfer of the genome between projects | learning dies with its repo; every project starts from zero |

The kernel's two atoms map cleanly: **attention** is triggering (skill descriptions always in
context, the constitution pointing at them, the miss-log catching what fell through) and
**trust** is the ladder plus the gates.

## The pipeline from vision to work

Human writes vision → a planning pass turns vision into `docs/state/roadmap.md` → the roadmap
yields chunks → each chunk runs in a bounded context against the relevant skill → gates pass →
state and log updated → commit → lessons (if any) become skill diffs → human reviews the diffs.
One human input at the top; one human checkpoint at every self-modification. Everything between
is the system's job.

## Scaling — the stress tests

One law underneath every answer: **context is working memory, files are long-term memory, and
the system scales only if working memory is never load-bearing.** The four moves are always the
same — externalize state to files, bound each context, gate every boundary, put the human at
the diff.

| Scaled to extreme | What breaks | The move |
|---|---|---|
| 1,000 skills | the always-loaded index itself | hub skills route to sub-skills; the manager consolidates by altitude and archives dead ones; the miss-log tells it what is missing rather than guessing |
| One massive task | no context can hold it | decompose into a plan file; chunks run in fresh bounded contexts (subagents); state written between chunks; every chunk gated |
| Many small tasks | per-task overhead dominates | a queue file, batch processing, and tools instead of the model wherever the step is mechanical |
| Massive refactor | invariants break silently | never refactor off a red baseline — the gates ARE the invariant; then chunk it like a massive task |
| Continuous surveillance / mass research digestion | the data outlives any context | the inbox pattern (TheBrain2): gather to files as `raw`, digest in a *fresh* context, emit a proposed skill diff, human reviews. Nothing is "remembered" — everything is written down |

## Resumability

The unit of progress is the chunk, and a chunk is not done until: **gates pass → `now.md` and
`log.md` updated → committed.** The commit is the atom of resumability. A cold start reads
vision → now → roadmap, in that order, and knows exactly where it stands.

The test is inherited from TheBrain2's cold-start quiz: periodically, a fresh subagent that has
seen nothing is asked "where is this project, what is the next action, and why?" — answerable
from the files alone. A wrong answer is a resumability bug, filed like any bug.

## Portability — if Claude Code disappears tomorrow

Three layers, strictly ordered by what they are allowed to contain:

1. **Knowledge and procedures** — markdown. Skill bodies, references, docs, state, decisions.
   Readable by any model, any harness, or a bare human. ALL content lives here.
2. **Contracts and gates** — `project.yaml`, the JSON Schema, pre-commit, CI, the tool itself.
   These run with no AI present at all.
3. **Harness bindings** — `.claude/` frontmatter, hook wiring, subagent config. Thin,
   regenerable, and containing zero knowledge. Pointers only (TheBrain2 Laws 8 and 12, ported).

The test: mentally delete layer 3. Nothing is lost but triggering convenience — `AGENTS.md`
points the next harness at the same markdown, and a human could follow the skills by hand.

## Context degradation

A model cannot reliably notice its own outputs degrading as context fills. That judgment stays
**human** — this is recorded as a permanent note, not a solved problem. The structural
mitigations don't depend on anyone noticing: chunks are bounded, graders always start fresh,
and the gates are deterministic — a degraded agent still cannot merge code that fails them.
Subagents are today's mechanism; the note outlives any mechanism. When in doubt, cut the
session and lean on resumability. That is what it is for.

## The CLI, after the pivot

The tool answers questions. It does not write your project.

| Command | Purpose |
|---|---|
| `initc validate` | is `project.yaml` well-formed and internally consistent |
| `initc doctor` | is this machine, and this checkout, ready to work — three states, every problem prints its fix |
| `initc env` | regenerate `.env.example` from the declared env contract |
| `initc run <task>` | run a declared task from anywhere in the tree |
| `initc lint-paths` | no absolute paths, ever |
| `initc schema` | export the JSON Schema, so editors validate `project.yaml` |
| `initc describe` | *(new)* inspect an existing repo, write the `project.yaml` describing it |
| `initc spawn <path>` | *(later)* copy this project's evolved genome into a new project |
| `initc absorb <path>` | *(later)* propose skills and standards learned from another repo |

`initc init` is gone. Installing is no longer a special mode — it is a declared task
(`tasks: {install: "uv sync"}`), so `initc run install` does it and `doctor` verifies it worked.
That single change deletes `local_mode`, `install_steps`, and the entire preset dispatch.

## What is deliberately not here

- **No framework axis, ever.** A vendored Next.js template is stale in six months;
  `create-next-app` never is, because the obligation to keep it fresh sits with the team that
  ships it. The base describes a framework; it does not create one.
- **No generated Dockerfiles.** Docker knowledge becomes `references/docker.md`, written by the
  agent against what is true today.
- **No opinionated defaults smuggled in as templates.** The phase-0 interview makes every opinion
  an explicit, recorded choice.

## Honest limits — where it is not perfect

"Perfect" is not a claim this system gets to make; the kernel's own standard is falsification —
find a problem that no cheap edit at any altitude absorbs. These are the standing candidates,
kept here so nobody has to rediscover them:

1. **Direction stays human, and that is a dependency, not a feature request.** The system can
   evolve every skill and still optimize beautifully toward a wrong vision. Only the human never
   goes static. If the vision is wrong, everything downstream is efficiently wrong.
2. **Feedback-starved domains.** The system is strongest exactly where reality answers in exit
   codes. Where feedback is slow, expensive, or ambiguous — product-market fit, design taste,
   research quality — gates cannot be deterministic, graders drift, and plausible-but-wrong
   survives. Mitigation, not cure: mark slow-signal claims as such, give them expiry dates,
   prefer the cheapest available reality-check over any rubric.
3. **The reviewer bottleneck.** Every self-modification funnels through one human's diff review.
   At scale that attention is the scarcest resource in the system: immunity degrades into
   rubber-stamping, or velocity dies. Mitigations: batch diffs, rank by risk, keep gate-covered
   changes light to review. This — not model quality — is the real scaling ceiling.
4. **Verifier rot.** Gates themselves rot, and a gate that silently passes everything is worse
   than no gate. Generalize the regression-test lesson: a check you have never watched fail is
   not a check. Periodically plant a violation and watch each gate catch it.
5. **Novelty.** A genuinely new task-shape has no skill. The miss-log makes the gap visible —
   but only if it is maintained. An unlogged miss is the system silently deciding it is complete.
6. **Non-reproducibility.** An agent bootstrapping a project is not byte-reproducible; acceptable
   **only because the gate is loud**. Reproducibility lives in `project.yaml` + doctor + the
   suite, not in file bytes. (This is also what makes it beginner-friendly: a beginner does not
   read the scaffold, they run `initc doctor` and every problem prints its fix.)
7. **Self-entrenchment.** A self-evolving system with no immune response converges on its own
   errors. The diff review and the trust ladder are not ceremony. They are the mechanism.

## The tree (as built, 2026-07-10)

```
init-configurator/
├── CLAUDE.md                    constitution: how to think; thin; always loaded
├── AGENTS.md                    one-line pointer at CLAUDE.md for other harnesses
├── README.md · LICENSE          the public face (MIT)
├── project.yaml                 this repo described, machine-checkably (dogfood)
├── pyproject.toml · uv.lock     the tool's own packaging + locked deps
├── .gitattributes               * text=auto eol=lf — git can't undo LF writes
├── .gitignore
├── .pre-commit-config.yaml      this repo runs its own path-lint hook
├── .pre-commit-hooks.yaml       lets OTHER repos consume path-lint as a hook
├── .github/workflows/ci.yml     the gates in CI, both OSes, schema-drift check
├── .claude/skills/              THE GENOME (layer 1+3: knowledge, thin bindings)
│   ├── project-base/            binds every session: gates, conventions, module map
│   ├── bootstrap/               phase 0: interview → official creator → describe → prove
│   │   └── references/          python.md · node.md · react.md · docker.md · quality-tools.md
│   ├── evolve/                  lesson → procedure → reviewed skill diff
│   ├── skill-manager/           altitude, consolidation, thresholds, miss-log, decay
│   ├── scale/                   the four moves; the five stress patterns; cold-start quiz
│   ├── absorb/                  conjugation: absorb genes in, spawn genome out
│   └── rot-check/               watch-the-gate-fail; stale-pin hunt; trust decay
├── src/init_configurator/       THE TOOL (layer 2: deterministic, runs without AI)
│   ├── manifest.py  doctor.py  runtimes.py  env_contract.py
│   ├── path_lint.py  paths.py  runner.py  beacons.py  textfile.py
│   ├── describe.py              read an existing repo → draft its project.yaml
│   └── cli.py                   validate · doctor · env · run · lint-paths · schema ·
│                                describe   (later: spawn · absorb)
├── schema/project.schema.json   generated, committed, CI-diffed
├── tests/                       flat, 1:1 with modules + conftest fixtures
└── docs/
    ├── vision.md                human-owned WHY (only Stepan edits; awaiting him)
    ├── state/                   now.md · roadmap.md · log.md · miss-log.md (resumability)
    ├── decisions/               ADRs (0001 = this amputation)
    ├── design/                  agentic-base.md (this file) · manifest-v1.md
    ├── structure.md             every file explained in a line — the map
    └── reviews/                 the adversarial reviews — the record
```

## Scope fork (open, deliberately undecided)

Two futures, not mutually exclusive but differently sequenced:

- **The portfolio-scoped base** — this repo, open source, shippable soon: the durable tool +
  the genome for software projects + the pivot story in `docs/reviews/`. Serves the job-first
  north star (TheBrain2 Law 11).
- **The generalized system** — everything in Part II at full scope: any task, any stage,
  possibly a separate, possibly closed project. TheBrain2 rebuilt on an executable substrate.

The base is the seed of the system either way; nothing in Part I is thrown away by Part II.
What is *not* yet decided is when the second scope opens, and Law 11 has a vote.
