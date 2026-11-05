"""
Unit tests for the Command Notebook module.
"""
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from app.ui.command_notebook import (
    CommandNotebook,
    CATEGORIES,
    RISK_LEVELS,
    LIBRARY_FILE,
    NOTEBOOK_DIR,
    load_library,
    save_library,
)


class TestCommandNotebook(unittest.TestCase):
    """Tests for the CommandNotebook core module."""

    def setUp(self):
        """Create a temporary directory for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.test_lib_file = os.path.join(self.test_dir, "library.json")

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _patch_paths(self, notebook):
        """Patch LIBRARY_FILE and NOTEBOOK_DIR to point to test dir."""
        import app.ui.command_notebook as cn
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        notebook.library = load_library()

    def test_default_categories_exist(self):
        """All 18 required categories exist."""
        self.assertEqual(len(CATEGORIES), 18)
        expected = [
            "ubuntu_system", "python_deps", "git_github",
            "docker_engine", "docker_compose", "docker_networks",
            "traefik", "ansible", "jenkins",
            "postgresql", "odoo17", "odoo18", "odoo19",
            "django", "portainer", "backup_restore",
            "ssl_security", "monitoring",
        ]
        for key in expected:
            self.assertIn(key, CATEGORIES)

    def test_load_library_creates_default(self):
        """Loading a missing library creates default with built-in commands."""
        import app.ui.command_notebook as cn
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        lib = load_library()
        self.assertIn(lib["version"], ("1.0", "1.1"))
        self.assertIn("categories", lib)
        self.assertIn("commands", lib)
        self.assertGreater(len(lib["commands"]), 0)
        self.assertTrue(os.path.exists(self.test_lib_file))

    def test_save_and_reload(self):
        """Saved library can be reloaded."""
        import app.ui.command_notebook as cn
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        lib = load_library()
        original_count = len(lib["commands"])
        save_library(lib)
        lib2 = load_library()
        self.assertEqual(len(lib2["commands"]), original_count)

    def test_add_command(self):
        """Adding a command persists it."""
        import app.ui.command_notebook as cn
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        notebook = CommandNotebook()
        self._patch_paths(notebook)
        initial_count = notebook.count()
        cmd_id = notebook.add_command(
            name="Test Command",
            command="echo hello",
            category="ubuntu_system",
            description="A test command",
            risk_level="low",
        )
        self.assertIsNotNone(cmd_id)
        self.assertEqual(notebook.count(), initial_count + 1)
        cmd = notebook.get_command(cmd_id)
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd["name"], "Test Command")
        self.assertEqual(cmd["command"], "echo hello")
        self.assertEqual(cmd["category"], "ubuntu_system")
        self.assertEqual(cmd["source"], "user")

    def test_add_command_unknown_category_raises(self):
        """Adding a command with unknown category raises ValueError."""
        import app.ui.command_notebook as cn
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        notebook = CommandNotebook()
        self._patch_paths(notebook)
        with self.assertRaises(ValueError):
            notebook.add_command(
                name="Test",
                command="echo",
                category="nonexistent_category",
            )

    def test_update_command(self):
        """Updating a command modifies its fields."""
        import app.ui.command_notebook as cn
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        notebook = CommandNotebook()
        self._patch_paths(notebook)
        cmd_id = notebook.add_command(
            name="Original",
            command="echo original",
            category="ubuntu_system",
        )
        notebook.update_command(
            cmd_id=cmd_id,
            name="Updated Name",
            command="echo updated",
            risk_level="high",
        )
        cmd = notebook.get_command(cmd_id)
        self.assertEqual(cmd["name"], "Updated Name")
        self.assertEqual(cmd["command"], "echo updated")
        self.assertEqual(cmd["risk_level"], "high")
        self.assertNotEqual(cmd["modified_at"], cmd["created_at"])

    def test_update_command_not_found_raises(self):
        """Updating a non-existent command raises KeyError."""
        import app.ui.command_notebook as cn
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        notebook = CommandNotebook()
        self._patch_paths(notebook)
        with self.assertRaises(KeyError):
            notebook.update_command(cmd_id="nonexistent", name="New")

    def test_delete_command(self):
        """Deleting a command removes it."""
        import app.ui.command_notebook as cn
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        notebook = CommandNotebook()
        self._patch_paths(notebook)
        initial_count = notebook.count()
        cmd_id = notebook.add_command(
            name="To Delete",
            command="echo delete",
            category="ubuntu_system",
        )
        notebook.delete_command(cmd_id)
        self.assertEqual(notebook.count(), initial_count)
        self.assertIsNone(notebook.get_command(cmd_id))

    def test_delete_command_not_found_raises(self):
        """Deleting a non-existent command raises KeyError."""
        import app.ui.command_notebook as cn
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        notebook = CommandNotebook()
        self._patch_paths(notebook)
        with self.assertRaises(KeyError):
            notebook.delete_command(cmd_id="nonexistent")

    def test_search_commands(self):
        """Search finds commands by name, command text, or category."""
        import app.ui.command_notebook as cn
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        notebook = CommandNotebook()
        self._patch_paths(notebook)
        notebook.add_command(
            name="My Custom Backup",
            command="mysqldump --all-databases",
            category="backup_restore",
        )
        notebook.add_command(
            name="Docker Run",
            command="docker run nginx",
            category="docker_engine",
        )
        # Search by name
        results = notebook.search("Custom Backup")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "My Custom Backup")
        # Search by command text
        results = notebook.search("mysqldump")
        self.assertEqual(len(results), 1)
        # Search by category name
        results = notebook.search("backup")
        self.assertGreaterEqual(len(results), 1)
        # Search returns nothing for non-match
        results = notebook.search("zzznothing")
        self.assertEqual(len(results), 0)

    def test_get_categories(self):
        """get_categories returns all categories with counts."""
        import app.ui.command_notebook as cn
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        notebook = CommandNotebook()
        self._patch_paths(notebook)
        cats = notebook.get_categories()
        self.assertEqual(len(cats), 18)
        for cat in cats:
            self.assertIn("key", cat)
            self.assertIn("name", cat)
            self.assertIn("count", cat)

    def test_get_commands_by_category(self):
        """get_commands_by_category returns commands with display numbers."""
        import app.ui.command_notebook as cn
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        notebook = CommandNotebook()
        self._patch_paths(notebook)
        cmds = notebook.get_commands_by_category("ubuntu_system")
        # Built-in commands should exist
        self.assertGreater(len(cmds), 0)
        for cmd in cmds:
            self.assertIn("display_number", cmd)
            self.assertIn("id", cmd)
            self.assertIn("name", cmd)

    def test_builtin_vs_user_distinction(self):
        """Built-in and user commands are distinguished."""
        import app.ui.command_notebook as cn
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        notebook = CommandNotebook()
        self._patch_paths(notebook)
        builtin_ids = notebook.get_builtin_command_ids()
        user_ids = notebook.get_user_command_ids()
        self.assertGreater(len(builtin_ids), 0)
        self.assertEqual(len(user_ids), 0)
        # Add a user command
        cmd_id = notebook.add_command(
            name="User Cmd",
            command="echo user",
            category="ubuntu_system",
        )
        user_ids = notebook.get_user_command_ids()
        self.assertIn(cmd_id, user_ids)

    def test_export_import(self):
        """Export and import round-trip works."""
        import app.ui.command_notebook as cn
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        notebook = CommandNotebook()
        self._patch_paths(notebook)
        notebook.add_command(
            name="Export Test",
            command="echo export",
            category="ubuntu_system",
        )
        export_path = os.path.join(self.test_dir, "export.json")
        notebook.export_library(export_path)
        self.assertTrue(os.path.exists(export_path))
        # Import into a fresh notebook
        notebook2 = CommandNotebook()
        self._patch_paths(notebook2)
        result = notebook2.import_library(export_path, merge=True)
        self.assertGreaterEqual(result["imported"], 1)

    def test_backup_created_on_save(self):
        """A backup file is created when saving an existing library."""
        import app.ui.command_notebook as cn
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        # Create initial library
        notebook = CommandNotebook()
        self._patch_paths(notebook)
        # Force a save to create the file
        save_library(notebook.library)
        # Modify and save again - backup should exist
        notebook.add_command(
            name="Backup Test",
            command="echo backup",
            category="ubuntu_system",
        )
        backups = [
            f for f in os.listdir(self.test_dir)
            if f.startswith("library.backup_") and f.endswith(".json")
        ]
        self.assertGreaterEqual(len(backups), 1)

    def test_reset_to_builtin(self):
        """Reset removes all user commands."""
        import app.ui.command_notebook as cn
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        notebook = CommandNotebook()
        self._patch_paths(notebook)
        notebook.add_command(
            name="Temp User",
            command="echo temp",
            category="ubuntu_system",
        )
        self.assertEqual(len(notebook.get_user_command_ids()), 1)
        notebook.reset_to_builtin()
        self.assertEqual(len(notebook.get_user_command_ids()), 0)
        self.assertGreater(len(notebook.get_builtin_command_ids()), 0)

    def test_risk_levels(self):
        """Risk levels are validated."""
        self.assertIn("low", RISK_LEVELS)
        self.assertIn("medium", RISK_LEVELS)
        self.assertIn("high", RISK_LEVELS)
        self.assertIn("critical", RISK_LEVELS)

    def test_multiline_command(self):
        """Multiline commands are stored correctly."""
        import app.ui.command_notebook as cn
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        notebook = CommandNotebook()
        self._patch_paths(notebook)
        multiline = "docker run -d \\\n  --name mycontainer \\\n  -p 80:80 \\\n  nginx"
        cmd_id = notebook.add_command(
            name="Multiline",
            command=multiline,
            category="docker_engine",
        )
        cmd = notebook.get_command(cmd_id)
        self.assertEqual(cmd["command"], multiline)

    def test_no_execution_engine_reference(self):
        """Verify the module does not import execution-related modules."""
        import app.ui.command_notebook as cn
        import ast
        with open(cn.__file__, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        forbidden = ["subprocess", "ansible", "jenkins"]
        for term in forbidden:
            self.assertNotIn(term, imports, f"Forbidden import '{term}' found in command_notebook.py")


if __name__ == "__main__":
    unittest.main()
