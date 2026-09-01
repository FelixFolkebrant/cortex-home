import ast
import unittest
from pathlib import Path


COORDINATOR_DIRECTORY = Path(__file__).parents[1]


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
        install = COORDINATOR_DIRECTORY.joinpath("install").read_text()
        install_host = COORDINATOR_DIRECTORY.joinpath("install-host").read_text()

        for module in required_modules:
            source_path = f'"$script_dir/{module}.py"'
            with self.subTest(module=module):
                self.assertIn(source_path, install)
                self.assertIn(source_path, install_host)

    def test_checks_the_installed_coordinator_import_before_restart(self):
        install_host = COORDINATOR_DIRECTORY.joinpath("install-host").read_text()

        self.assertIn(
            '/opt/cortex-home/venv/bin/python -c "import cortex_home"',
            install_host,
        )

    def test_installs_the_pinned_private_answer_runtime(self):
        install = COORDINATOR_DIRECTORY.joinpath("install").read_text()
        install_host = COORDINATOR_DIRECTORY.joinpath("install-host").read_text()
        requirements = COORDINATOR_DIRECTORY.joinpath("requirements.txt").read_text()
        service = COORDINATOR_DIRECTORY.joinpath(
            "files",
            "cortex-home.service",
        ).read_text()

        for artifact in [
            "agent-turn.js",
            "answer-child.js",
            "dialogue-child.js",
            "package.json",
            "pnpm-lock.yaml",
        ]:
            self.assertIn(f'"$script_dir/agent/{artifact}"', install)
        self.assertIn("node_version=24.18.0", install_host)
        self.assertIn(
            "55aa7153f9d88f28d765fcdad5ae6945b5c0f98a36881703817e4c450fa76742",
            install_host,
        )
        self.assertIn("pnpm@10.18.2", install_host)
        self.assertIn('["typebox", "1.1.38"]', install_host)
        self.assertEqual(
            install_host.count(
                "PATH=/opt/cortex-home/node/bin:/usr/sbin:/usr/bin:/sbin:/bin"
            ),
            2,
        )
        self.assertIn("--frozen-lockfile", install_host)
        self.assertIn("pocket-tts==2.1.0", requirements)
        self.assertIn("vosk==0.3.45", requirements)
        self.assertIn("vosk-model-small-en-us-0.15", install_host)
        self.assertIn("get_state_for_audio_prompt(\"alba\")", install_host)
        self.assertIn("root:cortex-home 640", install_host)
        self.assertIn("EnvironmentFile=/etc/cortex-home/agent.env", service)
        self.assertIn(
            "Environment=HF_HOME=/opt/cortex-home/models/pocket-cache",
            service,
        )


if __name__ == "__main__":
    unittest.main()
