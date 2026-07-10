# init-configurator — clone-and-run for any project

On start, read `G:\PythonProjects\_for_me\The Brain v2\knowledge\projects\init-configurator.md`
for current project state. The `project-base` skill in this repo binds every session —
it carries the initc CLI surface, the module map, and the downstream discovery chain;
look THERE first, not here. This repo holds the CANONICAL template other portfolio
repos instantiate.

Scope v1 is feature-complete (manifest, local mode, path-lint, doctor, docker mode);
next is publish prep. Checks: `uv run initc run test|lint|typecheck` +
`uv run initc lint-paths` — all green before any commit.

Public showcase repo: code quality is the product. Fully-owned by Stepan (skill rule 1).
