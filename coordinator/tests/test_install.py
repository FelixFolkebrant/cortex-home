import ast
import unittest
from pathlib import Path


COORDINATOR_DIRECTORY = Path(__file__).parents[1]
PROJECT_DIRECTORY = COORDINATOR_DIRECTORY.parent
COORDINATOR_ROLE = PROJECT_DIRECTORY / "ops" / "roles" / "coordinator"


class InstallTests(unittest.TestCase):
    def test_deploys_every_local_coordinator_import(self):
        source = COORDINATOR_DIRECTORY.joinpath("cortex_home.py").read_text()
        tree = ast.parse(source)
        local_modules = {
            path.stem for path in COORDINATOR_DIRECTORY.glob("*.py")
        }
        imported_modules = {
            node.module.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        imported_modules.update(
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        required_modules = local_modules & imported_modules
        role_defaults = COORDINATOR_ROLE.joinpath("defaults", "main.yml").read_text()

        for module in required_modules:
            with self.subTest(module=module):
                self.assertIn(f"  - {module}.py", role_defaults)

    def test_checks_the_installed_coordinator_import_before_restart(self):
        install_tasks = COORDINATOR_ROLE.joinpath("tasks", "main.yml").read_text()

        self.assertIn("-c 'import cortex_home'", install_tasks)

    def test_installs_the_pinned_private_answer_runtime(self):
        role_defaults = COORDINATOR_ROLE.joinpath("defaults", "main.yml").read_text()
        install_tasks = COORDINATOR_ROLE.joinpath("tasks", "main.yml").read_text()
        requirements = COORDINATOR_DIRECTORY.joinpath("requirements.txt").read_text()
        service = COORDINATOR_DIRECTORY.joinpath(
            "files",
            "cortex-home.service",
        ).read_text()

        for artifact in [
            "agent-turn.ts",
            "answer-child.ts",
            "dialogue-child.ts",
            "package.json",
            "pnpm-lock.yaml",
        ]:
            self.assertIn(f"  - {artifact}", role_defaults)
        self.assertIn("coordinator_node_version: 24.18.0", role_defaults)
        self.assertIn(
            "55aa7153f9d88f28d765fcdad5ae6945b5c0f98a36881703817e4c450fa76742",
            role_defaults,
        )
        self.assertIn("coordinator_pnpm_version: 10.18.2", role_defaults)
        self.assertIn('["typebox", "1.1.38"]', install_tasks)
        self.assertIn("--frozen-lockfile", install_tasks)
        self.assertIn("pocket-tts==2.1.0", requirements)
        self.assertIn("vosk==0.3.45", requirements)
        self.assertIn("vosk-model-small-en-us-0.15", role_defaults)
        self.assertIn("get_state_for_audio_prompt", install_tasks)
        self.assertIn('coordinator_agent_environment.stat.mode == "0640"', install_tasks)
        self.assertIn("EnvironmentFile=/etc/cortex-home/agent.env", service)
        self.assertIn(
            "Environment=HF_HOME=/opt/cortex-home/models/pocket-cache",
            service,
        )

    def test_production_and_speech_share_one_playbook(self):
        playbook = PROJECT_DIRECTORY.joinpath(
            "ops",
            "playbooks",
            "coordinator.yml",
        ).read_text()
        install_tasks = COORDINATOR_ROLE.joinpath("tasks", "main.yml").read_text()

        self.assertIn("hosts: coordinators", playbook)
        self.assertIn("Install the speech qualification workbench", install_tasks)
        self.assertIn("- never", install_tasks)
        self.assertIn("- speech", install_tasks)
        self.assertFalse(COORDINATOR_DIRECTORY.joinpath("install").exists())
        self.assertFalse(COORDINATOR_DIRECTORY.joinpath("install-host").exists())


if __name__ == "__main__":
    unittest.main()
