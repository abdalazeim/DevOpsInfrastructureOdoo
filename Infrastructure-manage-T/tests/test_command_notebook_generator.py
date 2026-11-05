"""
Unit tests for the dynamic Odoo Docker command generator and notebook integration.

These tests validate generation/validation/persistence logic only.
They must not invoke subprocess, Docker, Ansible, Jenkins, or shell execution.
"""
import ast
import os
import shutil
import tempfile
import unittest

from app.ui.command_notebook_generator import (
    OdooGeneratorConfig,
    generate_odoo_commands,
    generate_compose_yaml,
    validate_config,
    config_signature,
)
from app.ui.command_notebook import CommandNotebook


class TestOdooCommandGenerator(unittest.TestCase):
    def test_generate_odoo17_18_19(self):
        for v, http, lp, pg in (("17", 10017, 20017, "16"), ("18", 10018, 20018, "17"), ("19", 10019, 20019, "18")):
            cfg = OdooGeneratorConfig(odoo_version=v, http_host_port=http, longpolling_host_port=lp)
            ok, cmds, errs, warns, compose = generate_odoo_commands(cfg)
            self.assertTrue(ok, f"Odoo {v} failed: {errs}")
            self.assertEqual(errs, [])
            self.assertGreaterEqual(len(cmds), 25)
            self.assertIn(f"odoo:{v}", compose)
            self.assertIn(f"postgres:{pg}", compose)
            self.assertIn(f'"{http}:8069"', compose)
            self.assertIn(f'"{lp}:8072"', compose)
            self.assertTrue(any(c.get("odoo_version") == v for c in cmds))

    def test_custom_ports_and_postgres_selection(self):
        cfg = OdooGeneratorConfig(
            odoo_version="19",
            http_host_port=18019,
            longpolling_host_port=28019,
            postgres_image="postgres:18-alpine",
            deployment_dir="/opt/odoo/custom19",
            compose_project_name="odoo19-custom",
        )
        ok, cmds, errs, _, compose = generate_odoo_commands(cfg)
        self.assertTrue(ok, errs)
        self.assertIn("18019:8069", compose)
        self.assertIn("28019:8072", compose)
        self.assertIn("postgres:18-alpine", compose)
        self.assertTrue(any("18019" in c["command"] for c in cmds))

    def test_port_validation_and_consistency(self):
        ok, errs, _ = validate_config(OdooGeneratorConfig(odoo_version="19", http_host_port=10019, longpolling_host_port=10019))
        self.assertFalse(ok)
        self.assertTrue(any("must be different" in e for e in errs))

        ok, errs, _ = validate_config(OdooGeneratorConfig(odoo_version="19", http_host_port=70000, longpolling_host_port=20019))
        self.assertFalse(ok)

        ok, errs, _ = validate_config(
            OdooGeneratorConfig(odoo_version="19", http_host_port=10019, longpolling_host_port=20019),
            used_host_ports={10019: "existing-service"},
        )
        self.assertFalse(ok)
        self.assertTrue(any("already assigned" in e for e in errs))

    def test_safety_requirements_in_generated_commands(self):
        ok, cmds, errs, _, compose = generate_odoo_commands(OdooGeneratorConfig(odoo_version="19"))
        self.assertTrue(ok, errs)
        all_text = "\n".join(c["command"] for c in cmds) + "\n" + compose
        self.assertNotIn("chmod -R 777", all_text)
        self.assertNotIn("chmod 777", all_text)
        # down -v must never be presented as a normal/default command
        self.assertTrue(any("down -v" in c["command"] and "NEVER" in c["command"] for c in cmds))
        self.assertTrue(all(c.get("risk_classification") in {"SAFE", "MODERATE", "HIGH", "DESTRUCTIVE"} for c in cmds))
        self.assertTrue(any(c.get("risk_classification") == "DESTRUCTIVE" for c in cmds))
        self.assertFalse(any("admin123" in c["command"].lower() or "password=odoo19" in c["command"].lower() for c in cmds))

    def test_compose_generator_has_required_sections(self):
        cfg = OdooGeneratorConfig(odoo_version="18", http_host_port=10018, longpolling_host_port=20018, docker_network="proxy")
        compose = generate_compose_yaml(cfg)
        for token in (
            "services:", "db:", "odoo:", "depends_on:", "service_healthy", "ports:", "10018:8069", "20018:8072",
            "restart:", "healthcheck:", "networks:", "odoo_internal", "proxy:", "external: true",
            "volumes:", "odoo_filestore", "POSTGRES_PASSWORD", "HOST: db",
        ):
            self.assertIn(token, compose)
        self.assertIn("postgres:17", compose)

    def test_profile_read_only_integration(self):
        class DB:
            engine = "postgres:17-alpine"
        class Inst:
            image = "odoo:18.0"
            domain = "odoo18.example.com"
            database = DB()
        class Paths:
            data_root = "/srv/odoo"
        class Net:
            proxy_network_name = "proxy-net"
        class Profile:
            odoo18 = Inst()
            paths = Paths()
            network = Net()
        cfg = OdooGeneratorConfig.from_profile(Profile(), odoo_version="18")
        self.assertEqual(cfg.odoo_version, "18")
        self.assertEqual(cfg.odoo_image, "odoo:18.0")
        self.assertEqual(cfg.postgres_image, "postgres:17-alpine")
        self.assertEqual(cfg.docker_network, "proxy-net")
        self.assertEqual(cfg.deployment_mode, "domain")
        self.assertEqual(cfg.domain, "odoo18.example.com")

    def test_config_signature_stable(self):
        a = OdooGeneratorConfig(odoo_version="17", http_host_port=10017)
        b = OdooGeneratorConfig(odoo_version="17", http_host_port=10017)
        c = OdooGeneratorConfig(odoo_version="17", http_host_port=10117)
        self.assertEqual(config_signature(a), config_signature(b))
        self.assertNotEqual(config_signature(a), config_signature(c))

    def test_generator_has_no_execution_engine_imports(self):
        import app.ui.command_notebook_generator as gen
        with open(gen.__file__, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        forbidden = ("subprocess", "docker", "ansible", "jenkins")
        for term in forbidden:
            self.assertFalse(any(term in m for m in imports), f"Forbidden import containing '{term}' in generator: {imports}")


class TestNotebookGeneratedCommandPersistence(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_lib_file = os.path.join(self.test_dir, "library.json")
        import app.ui.command_notebook as cn
        self.cn = cn
        self._orig_dir = cn.NOTEBOOK_DIR
        self._orig_file = cn.LIBRARY_FILE
        cn.NOTEBOOK_DIR = self.test_dir
        cn.LIBRARY_FILE = self.test_lib_file
        self.notebook = CommandNotebook()

    def tearDown(self):
        self.cn.NOTEBOOK_DIR = self._orig_dir
        self.cn.LIBRARY_FILE = self._orig_file
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_upsert_generated_preserves_user_modified(self):
        cfg = OdooGeneratorConfig(odoo_version="19")
        ok, cmds, errs, _, _ = generate_odoo_commands(cfg)
        self.assertTrue(ok, errs)
        self.notebook.upsert_generated_commands(cmds, cfg.to_metadata())
        # modify one generated command (simulating user edit)
        gen_cmd = next(c for c in self.notebook.library["commands"].values() if c.get("source") in ("generated", "user") and c.get("odoo_version") == "19")
        self.notebook.update_command(gen_cmd["id"], command=gen_cmd["command"] + "\n# user note")
        # regenerate with changed config
        cfg2 = OdooGeneratorConfig(odoo_version="19", http_host_port=18019, longpolling_host_port=28019)
        ok, cmds2, errs, _, _ = generate_odoo_commands(cfg2)
        self.assertTrue(ok, errs)
        stats = self.notebook.upsert_generated_commands(cmds2, cfg2.to_metadata())
        self.assertGreaterEqual(stats["kept_user_modified"], 1)
        edited = self.notebook.get_command(gen_cmd["id"])
        self.assertIn("# user note", edited["command"])


if __name__ == "__main__":
    unittest.main()
