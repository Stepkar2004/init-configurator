"""Starter files for a Node/TypeScript stack: strict tsconfig, Biome, Vitest.

Core preset only — React-specific lint layers and optional quality add-ons
(knip, dependency-cruiser, size-limit) are a scaffold-time choice in a later
phase, never forced.
"""

import json

from init_configurator.manifest import Manifest, Stack
from init_configurator.presets.common import stack_readme

GITIGNORE = """\
# Dependencies live INSIDE the project but never in git.
node_modules/
.env

# Build output
dist/
"""

INDEX_TS = """\
export const greeting = "hello from a fresh project";
"""

INDEX_TEST_TS = """\
// Starter test — replace with real tests as the project grows.
import { expect, test } from "vitest";

import { greeting } from "../src/index.js";

test("package exports something", () => {
  expect(greeting).toBeTruthy();
});
"""


def files(stack: Stack, manifest: Manifest, *, pnpm_version: str | None = None) -> dict[str, str]:
    """Starter files for one Node stack, keyed by stack-relative path."""
    return {
        "package.json": _package_json(stack, manifest, pnpm_version),
        "tsconfig.json": _tsconfig_json(),
        "tsconfig.build.json": _tsconfig_build_json(),
        "biome.json": _biome_json(),
        "src/index.ts": INDEX_TS,
        "tests/index.test.ts": INDEX_TEST_TS,
        ".gitignore": GITIGNORE,
        "README.md": stack_readme(manifest, stack),
    }


def _package_json(stack: Stack, manifest: Manifest, pnpm_version: str | None) -> str:
    """Build package.json programmatically — JSON braces and str.format don't mix."""
    content: dict[str, object] = {
        "name": manifest.project.name,
        "version": "0.1.0",
        "description": manifest.project.description,
        "private": True,
        "type": "module",
        "scripts": {
            # Two tsconfigs: `typecheck` covers src+tests and emits nothing;
            # `build` compiles src alone, so tests never land in dist/.
            "build": "tsc -p tsconfig.build.json",
            "typecheck": "tsc --noEmit",
            "test": "vitest run",
            "lint": "biome check .",
            "format": "biome format --write .",
        },
        "engines": {"node": f">={stack.version}"},
        "devDependencies": {
            "@biomejs/biome": "^2.0.0",
            "@tsconfig/strictest": "^2.0.0",
            "@types/node": f"^{stack.version.split('.')[0]}",
            "typescript": "^5.5.0",
            "vitest": "^3.0.0",
        },
    }
    # Pin the exact package manager via corepack's field — but only when we know
    # the real installed version; a made-up pin would break installs.
    if stack.package_manager == "pnpm" and pnpm_version:
        content["packageManager"] = f"pnpm@{pnpm_version}"
    return json.dumps(content, indent=2) + "\n"


def _tsconfig_json() -> str:
    """The typecheck surface: everything that is source, nothing emitted."""
    content = {
        "extends": "@tsconfig/strictest/tsconfig.json",
        "compilerOptions": {
            "module": "nodenext",
            "moduleResolution": "nodenext",
            "noEmit": True,
        },
        "include": ["src", "tests"],
    }
    return json.dumps(content, indent=2) + "\n"


def _tsconfig_build_json() -> str:
    """The build surface: src only, so `dist/` never contains compiled tests."""
    content = {
        "extends": "./tsconfig.json",
        "compilerOptions": {
            "noEmit": False,
            "rootDir": "src",
            "outDir": "dist",
        },
        "include": ["src"],
    }
    return json.dumps(content, indent=2) + "\n"


def _biome_json() -> str:
    content = {
        # Biome does not read .gitignore unless asked. Without this, `lint` after
        # a `build` checks the emitted dist/ and fails on generated code.
        "vcs": {"enabled": True, "clientKind": "git", "useIgnoreFile": True},
        "linter": {"enabled": True},
        "formatter": {"enabled": True, "indentStyle": "space"},
        # Every .json file here is machine-written by json.dumps, which always
        # expands. Biome's default collapses a short array onto one line, so a
        # fresh scaffold failed its own `lint` on the tsconfigs. Telling Biome
        # that JSON is expanded makes the generated files canonical, and leaves
        # the default heuristics in charge of the TypeScript the user writes.
        "json": {"formatter": {"expand": "always"}},
    }
    return json.dumps(content, indent=2) + "\n"
