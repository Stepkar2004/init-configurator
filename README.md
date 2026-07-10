# init-configurator

Clone any project. Run one command. It works.

- **Two install modes:** `--docker` (generated Dockerfile/compose) or `--local`
  (everything inside the project folder — venv, local node_modules; zero global installs)
- **path-lint:** pre-commit + CI check that rejects absolute paths — root-relative or it
  doesn't merge
- **`init doctor`:** tells you what's missing *before* setup fails, not during
- **`.env` contract:** required vars declared in the manifest, checked, templated

Status: v1 in progress. Demo screencasts (fresh-machine clone → running, both modes)
land here when v1 ships.
