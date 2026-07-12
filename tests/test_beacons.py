"""Tests for the beacon templates a bootstrapped project receives.

beacons.py is the template SOURCE the bootstrap skill materializes; nothing in
this repo executes it at runtime anymore, which is exactly how stale content
would ship silently. These tests hold the generated text to the current world:
the constitution IS the instruction layer (no separate project skill), it speaks
the post-pivot CLI, and the append variant never claims to own the file.
"""

from init_configurator.beacons import (
    constitution,
    context_beacons,
    pointer_block,
)
from tests.conftest import ManifestFactory


class TestContextBeacons:
    def test_claude_primary_makes_agents_the_pointer(self, build_manifest: ManifestFactory) -> None:
        files = context_beacons(build_manifest(), agent="claude")
        assert "single source of truth" in files["CLAUDE.md"]
        assert "CLAUDE.md" in files["AGENTS.md"]  # the pointer names its target
        assert len(files["AGENTS.md"].splitlines()) < len(files["CLAUDE.md"].splitlines())

    def test_agents_primary_flips_the_pair(self, build_manifest: ManifestFactory) -> None:
        files = context_beacons(build_manifest(), agent="agents")
        assert "single source of truth" in files["AGENTS.md"]
        assert "AGENTS.md" in files["CLAUDE.md"]

    def test_primary_points_at_the_skills_and_the_manifest(
        self, build_manifest: ManifestFactory
    ) -> None:
        primary = context_beacons(build_manifest(), agent="claude")["CLAUDE.md"]
        assert ".claude/skills/" in primary and "workflow" in primary  # the skill index
        # "where things live" points at project.yaml, not a copied-out task list that rots
        assert "project.yaml" in primary and "docs/state/" in primary
        assert "initc run <task>" in primary


class TestConstitution:
    def test_speaks_the_task_model_not_init(self, build_manifest: ManifestFactory) -> None:
        content = constitution(build_manifest())
        assert "initc run <task>" in content  # points at the task runner, not a copied list
        assert "initc doctor" in content
        assert "initc init" not in content  # the command no longer exists

    def test_carries_the_binding_rules(self, build_manifest: ManifestFactory) -> None:
        content = constitution(build_manifest())
        assert "single source of truth" in content and "project.yaml" in content
        assert "NEVER push" in content
        assert "docs/posts/" in content and "em dashes" in content
        assert "evolve" in content  # lessons land in a skill, not this file


class TestPointerBlock:
    def test_appends_without_claiming_ownership(self) -> None:
        block = pointer_block()
        assert block.startswith("\n")  # appended after existing content, not overwriting
        assert "Safe to edit or remove" in block
        assert ".claude/skills/workflow/SKILL.md" in block
        assert "single source of truth" in block
