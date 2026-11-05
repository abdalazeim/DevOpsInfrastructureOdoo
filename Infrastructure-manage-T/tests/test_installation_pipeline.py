"""
Unit tests for the Installation Pipeline module.
"""
import unittest
from unittest.mock import patch, MagicMock

from app.core.installation_pipeline import (
    InstallationPipeline,
    StepResult,
    ComponentPipelineRecord,
    InstallationStatus,
)


class TestInstallationPipeline(unittest.TestCase):
    """Tests for the InstallationPipeline core module."""

    def setUp(self):
        self.log_messages = []
        self.pipeline = InstallationPipeline(
            dry_run=True,
            use_sudo=False,
            on_output=lambda msg: self.log_messages.append(msg),
        )

    def test_default_components_count(self):
        """Pipeline has expected default components."""
        self.assertEqual(len(self.pipeline._component_defs), 13)

    def test_component_names(self):
        """Expected component names exist."""
        names = [c["name"] for c in self.pipeline._component_defs]
        expected = [
            "ubuntu_preparation",
            "python_install",
            "git_install",
            "docker_engine",
            "docker_compose",
            "docker_network",
            "odoo_version_select",
            "postgresql",
            "odoo_install",
            "traefik_install",
            "ansible_install",
            "jenkins_install",
            "final_integration",
        ]
        for name in expected:
            self.assertIn(name, names)
        self.assertEqual(len(names), len(expected))

    def test_dependency_order(self):
        """Dependencies are computed in correct topological order."""
        order = self.pipeline._compute_install_order()
        # ubuntu_preparation should be first (no deps)
        self.assertEqual(order[0], "ubuntu_preparation")
        # docker_compose depends on docker_engine, so engine comes first
        de_idx = order.index("docker_engine")
        dc_idx = order.index("docker_compose")
        self.assertLess(de_idx, dc_idx)
        # traefik depends on odoo_install
        odoo_idx = order.index("odoo_install")
        traefik_idx = order.index("traefik_install")
        self.assertLess(odoo_idx, traefik_install_idx if False else traefik_idx)
        # final_integration depends on odoo, traefik, ansible, jenkins
        fi_idx = order.index("final_integration")
        self.assertGreater(fi_idx, odoo_idx)
        self.assertGreater(fi_idx, traefik_idx)

    def test_can_install_blocks_on_failed_dependency(self):
        """Component with failed dependency cannot be installed."""
        # Mark docker_engine as failed
        self.pipeline._failed_components.add("docker_engine")
        self.assertFalse(self.pipeline._can_install("docker_compose"))

    def test_can_install_allows_independent(self):
        """Independent components can still be installed when dependency fails."""
        self.pipeline._failed_components.add("docker_engine")
        # git_install depends only on ubuntu_preparation, not docker_engine
        self.assertTrue(self.pipeline._can_install("git_install"))

    def test_run_step_dry_run(self):
        """Dry-run step succeeds without executing."""
        result = self.pipeline._run_step("test", ["echo", "hello"])
        self.assertTrue(result.success)
        self.assertTrue(result.verified)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("[DRY-RUN]", result.stdout)

    def test_generate_report_structure(self):
        """Report contains expected keys."""
        report = self.pipeline.generate_report()
        self.assertIn("overall_success", report)
        self.assertIn("success_count", report)
        self.assertIn("failure_count", report)
        self.assertIn("skip_count", report)
        self.assertIn("total", report)
        self.assertIn("install_order", report)
        self.assertIn("components", report)

    def test_get_progress(self):
        """Progress tracking works."""
        progress = self.pipeline.get_progress()
        self.assertIn("total", progress)
        self.assertIn("completed", progress)
        self.assertIn("percent", progress)
        self.assertIn("stages", progress)
        self.assertEqual(progress["total"], 13)

    def test_blocked_component_propagation(self):
        """When a component fails, its dependents are blocked."""
        self.pipeline._failed_components.add("docker_engine")
        # docker_compose depends on docker_engine -> blocked
        self.assertFalse(self.pipeline._can_install("docker_compose"))
        # traefik_install depends on odoo_install -> odoo depends on postgresql -> postgresql depends on docker_network -> docker_network depends on docker_engine
        # So traefik should be blocked too
        self.assertFalse(self.pipeline._can_install("traefik_install"))

    def test_step_result_properties(self):
        """StepResult properties work correctly."""
        step = StepResult(
            name="test",
            command=["echo", "hi"],
            exit_code=0,
            stdout="hi",
            stderr="",
            start_time="2026-01-01T00:00:00+00:00",
            end_time="2026-01-01T00:00:01+00:00",
            duration_seconds=1.0,
            success=True,
            verified=True,
            verification_detail="OK",
        )
        self.assertEqual(step.command_str, "echo hi")
        self.assertTrue(step.success)

    def test_component_record_all_steps_passed(self):
        """ComponentPipelineRecord.all_steps_passed works."""
        record = ComponentPipelineRecord(name="test", category="cat")
        self.assertTrue(record.all_steps_passed)  # no steps = vacuously true
        record.steps.append(StepResult(
            name="s1", command=[], exit_code=0, stdout="", stderr="",
            start_time="", end_time="", duration_seconds=0, success=True,
        ))
        self.assertTrue(record.all_steps_passed)
        record.steps.append(StepResult(
            name="s2", command=[], exit_code=1, stdout="", stderr="",
            start_time="", end_time="", duration_seconds=0, success=False,
        ))
        self.assertFalse(record.all_steps_passed)

    def test_component_record_failed_step(self):
        """ComponentPipelineRecord.failed_step works."""
        record = ComponentPipelineRecord(name="test", category="cat")
        self.assertIsNone(record.failed_step)
        record.steps.append(StepResult(
            name="s1", command=[], exit_code=0, stdout="", stderr="",
            start_time="", end_time="", duration_seconds=0, success=True,
        ))
        self.assertIsNone(record.failed_step)
        record.steps.append(StepResult(
            name="s2", command=[], exit_code=1, stdout="", stderr="",
            start_time="", end_time="", duration_seconds=0, success=False,
        ))
        self.assertEqual(record.failed_step.name, "s2")


class TestInstallationPipelineExecution(unittest.TestCase):
    """Tests for pipeline execution with mocked subprocess."""

    def setUp(self):
        self.log_messages = []

    @patch("app.core.installation_pipeline.subprocess.run")
    def test_pipeline_dry_run_executes_all_stages(self, mock_run):
        """Dry-run pipeline completes all stages without calling subprocess."""
        pipeline = InstallationPipeline(
            dry_run=True,
            on_output=lambda msg: self.log_messages.append(msg),
        )
        report = pipeline.run()
        # subprocess should not be called in dry-run
        mock_run.assert_not_called()
        # All components should be installed (dry-run always succeeds)
        self.assertEqual(report["failure_count"], 0)
        self.assertEqual(report["success_count"], len(pipeline._component_defs))

    @patch("app.core.installation_pipeline.subprocess.run")
    def test_pipeline_failure_blocks_dependents(self, mock_run):
        """Failed component blocks its dependents."""
        # Make docker_engine fail
        def side_effect(cmd, **kwargs):
            mock = MagicMock()
            if "docker" in str(cmd) and "compose" not in str(cmd):
                mock.returncode = 1
                mock.stdout = ""
                mock.stderr = "docker not found"
            else:
                mock.returncode = 0
                mock.stdout = "OK"
                mock.stderr = ""
            return mock

        mock_run.side_effect = side_effect

        pipeline = InstallationPipeline(
            dry_run=False,
            on_output=lambda msg: self.log_messages.append(msg),
        )
        report = pipeline.run()

        # docker_engine should have failed
        self.assertIn("docker_engine", report["failed_components"])
        # docker_compose depends on docker_engine -> should be skipped/blocked
        self.assertIn("docker_compose", report["blocked_components"])

    def test_odoo_versions_constant(self):
        """ODOO_VERSIONS constant has expected versions."""
        from app.ui.installation_pipeline_ui import ODOO_VERSIONS
        self.assertIn("17", ODOO_VERSIONS)
        self.assertIn("18", ODOO_VERSIONS)
        self.assertIn("19", ODOO_VERSIONS)
        self.assertEqual(ODOO_VERSIONS["19"]["port"], 10019)
        self.assertEqual(ODOO_VERSIONS["17"]["port"], 10017)


if __name__ == "__main__":
    unittest.main()
