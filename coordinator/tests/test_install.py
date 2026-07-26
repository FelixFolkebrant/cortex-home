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


if __name__ == "__main__":
    unittest.main()
