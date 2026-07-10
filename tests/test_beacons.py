"""Tests for the beacon templates a bootstrapped project receives.

beacons.py is the template SOURCE the bootstrap skill materializes; nothing in
this repo executes it at runtime anymore, which is exactly how stale content
would ship silently. These tests hold the generated text to the post-pivot
world: the task model, the discovery chain, and no trace of removed commands.
"""

from init_configurator.beacons import SKILL_PATH, context_beacons, project_skill
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

    def test_primary_lists_the_declared_tasks(self, build_manifest: ManifestFactory) -> None:
        primary = context_beacons(build_manifest(), agent="claude")["CLAUDE.md"]
        assert "initc run test" in primary
        assert primary.count(SKILL_PATH) >= 1  # the discovery chain's next link


class TestProjectSkill:
    def test_skill_teaches_the_task_model_not_init(self, build_manifest: ManifestFactory) -> None:
        content = project_skill(build_manifest())[SKILL_PATH]
        assert "initc run install" in content
        assert "initc init" not in content  # the command no longer exists
        assert "initc doctor" in content

    def test_skill_carries_the_env_rule_and_evolution_marker(
        self, build_manifest: ManifestFactory
    ) -> None:
        content = project_skill(build_manifest())[SKILL_PATH]
        assert "env" in content and "project.yaml" in content
        assert "<!-- self-evolution starts here -->" in content
