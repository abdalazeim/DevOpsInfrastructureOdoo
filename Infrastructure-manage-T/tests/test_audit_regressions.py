"""Regression cases reproduced in the three audits. Never touch a Docker host."""
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.final_workflow import FinalWorkflow, PHASES
from app.core.installation_pipeline import InstallationPipeline
from app.core.server_setup import ServerSetupWorkflow
from app.models.profile import InfrastructureProfile
from app.services import odoo_service as odoo
from app.services import uninstall_service as cleanup
from app.services.instance_backup import load_verified, restore, extract
from app.services.managed_stack import stack_spec, deploy
from app.services.system_backup import SystemBackupService


class AuditRegressions(unittest.TestCase):
    def profile(self):
        return InfrastructureProfile.from_dict({'odoo18': {'enabled': False}, 'odoo19': {'enabled': False}})

    def inspect(self, rows):
        with patch.object(odoo.shutil, 'which', return_value='docker'), patch.object(odoo, 'probe',
                return_value=(0, '\n'.join(json.dumps(row) for row in rows))):
            return odoo.inspect_odoo('17')

    def test_wrong_images_are_conflicts(self):
        self.assertEqual(self.inspect([{'Names': 'odoo17', 'Image': 'nginx:latest'},
                                       {'Names': 'odoo17-db', 'Image': 'redis:latest'}])['status'], 'conflict')

    def test_multi_instance_pair_recognized(self):
        self.assertEqual(self.inspect([{'Names': 'odoo17-instance1', 'Image': 'odoo:17.0'},
            {'Names': 'odoo17-instance1-db', 'Image': 'postgres:16-alpine'}])['status'], 'installed')

    def test_unrelated_postgres_ignored(self):
        self.assertEqual(self.inspect([{'Names': 'other-db', 'Image': 'postgres:16'}])['status'], 'missing')

    def test_paused_not_healthy(self):
        rows = [{'Names': 'odoo17', 'Image': 'odoo:17', 'Status': 'Up 2 hours (Paused)'},
                {'Names': 'odoo17-db', 'Image': 'postgres:16', 'Status': 'Up 2 hours'}]
        with patch.object(odoo.shutil, 'which', return_value='docker'), patch.object(odoo, 'inspect_odoo',
                return_value={'status': 'installed', 'containers': rows}), patch.object(odoo.socket, 'socket'), \
                patch.object(odoo.os.path, 'exists', return_value=True):
            issues, _ = odoo.odoo_diagnose('17')
        self.assertIn('odoo17_container_not_running', [i['id'] for i in issues])

    def test_protected_child_blocks_parent_removal(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp) / 'installation'
            (parent / 'backups').mkdir(parents=True)
            (parent / 'backups' / 'db.sql').write_text('important')
            with patch.object(cleanup, 'PROJECT_INSTALL_PATHS', [str(parent)]), \
                    patch.object(cleanup, '_run', return_value=(1, '', '')):
                self.assertTrue(cleanup.should_protect(str(parent))[0])
                item = cleanup.CleanupItem('parent', 'directory', str(parent), 'test')
                executor = cleanup.UninstallExecutor(log_file=str(Path(tmp) / 'log'))
                with patch.object(cleanup.shutil, 'rmtree') as remove:
                    executor.execute_item(item)
                    remove.assert_not_called()

    def test_pipeline_contains_no_placeholder_installation(self):
        pipeline = InstallationPipeline(profile=self.profile())
        for component in pipeline._component_defs:
            for command in component['install_cmds'] + component['verify_cmds']:
                self.assertFalse(len(command) > 2 and command[:2] == ['bash', '-c'] and command[2].startswith('echo ') and '|' not in command[2] and '>' not in command[2]))
        self.assertNotIn('odoo18', [c['name'] for c in pipeline._component_defs])

    def test_unknown_inspection_cannot_pass(self):
        setup = ServerSetupWorkflow(self.profile())
        with patch('app.core.server_setup.subprocess.run', side_effect=FileNotFoundError('bash')):
            self.assertFalse(setup.run_ordered_installation()['overall_success'])

    def test_transitive_block_preserves_independent_component(self):
        pipeline = InstallationPipeline(profile=self.profile())
        pipeline._failed_components.add('docker-engine')
        self.assertFalse(pipeline._can_install('odoo17'))
        self.assertTrue(pipeline._can_install('git'))

    def test_dry_run_is_not_verified_and_calls_nothing(self):
        pipeline = InstallationPipeline(profile=self.profile(), dry_run=True)
        with patch('subprocess.run') as run:
            report = pipeline.run()
            run.assert_not_called()
        self.assertEqual(report['success_count'], 0)
        self.assertTrue(all(not step.verified for r in report['components'].values() for step in r.steps))

    def test_local_stack_credentials_and_storage(self):
        spec = stack_spec(self.profile(), '17', 'secret-test-value')
        app, db = spec['services']['odoo'], spec['services']['db']
        self.assertEqual(app['environment']['PASSWORD'], db['environment']['POSTGRES_PASSWORD'])
        self.assertEqual(app['environment']['HOST'], 'odoo17-db')
        self.assertNotIn('DB_HOST', app['environment'])
        self.assertIn('127.0.0.1:10017:8069', app['ports'])
        self.assertNotIn('ports', db)

    def test_postgres18_volume_layout(self):
        profile = self.profile()
        spec = stack_spec(profile, '19', 'test')
        self.assertIn('database:/var/lib/postgresql', spec['services']['db']['volumes'])

    def test_existing_stack_never_recreated(self):
        with patch('app.services.managed_stack.run'), patch('app.services.managed_stack.subprocess.run',
                return_value=subprocess.CompletedProcess([], 0)), patch('app.services.managed_stack.verify') as verify:
            deploy(self.profile(), '17')
            verify.assert_called_once_with('17')

    def test_dump_access_failure_is_fatal(self):
        with patch.object(SystemBackupService, '_run_docker_cmd', return_value=(1, '', 'denied')):
            with self.assertRaises(RuntimeError):
                SystemBackupService._dump_databases('unused')

    def test_restore_requires_confirmation_before_docker(self):
        with patch('app.services.instance_backup.docker') as docker:
            with self.assertRaises(ValueError):
                restore('not-a-path', 'unused')
            docker.assert_not_called()

    def test_incomplete_backup_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'manifest.json').write_text(json.dumps({'format': 1, 'status': 'completed', 'files': {}}))
            with self.assertRaises(ValueError):
                load_verified(tmp)

    def test_tar_traversal_rejected(self):
        import tarfile
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'bad.tar.gz'
            with tarfile.open(archive, 'w:gz') as tar:
                tar.addfile(tarfile.TarInfo('../outside'))
            with self.assertRaises(ValueError):
                extract(archive, Path(tmp) / 'destination')

    def test_full_workflow_dry_run_has_no_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'reports'
            with patch('subprocess.run') as run:
                result = FinalWorkflow(self.profile(), target, dry_run=True, output=lambda _: None).run()
                run.assert_not_called()
            self.assertFalse(target.exists())
            self.assertEqual(len(result['phases']), len(PHASES))
            self.assertEqual(result['completed_percent'], 0)
            self.assertEqual(result['status'], 'NOT READY')

    def test_non_ubuntu_never_installs(self):
        with tempfile.TemporaryDirectory() as tmp, patch('app.core.final_workflow.platform.system', return_value='Windows'), \
                patch.object(InstallationPipeline, 'run') as run:
            result = FinalWorkflow(self.profile(), tmp, apply=True, output=lambda _: None).run()
            run.assert_not_called()
            self.assertEqual(result['status'], 'NOT READY')

    def test_resume_rejects_changed_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'workflow-state.json').write_text(json.dumps({'profile_hash': 'different'}))
            with self.assertRaises(ValueError):
                FinalWorkflow(self.profile(), tmp, resume=True).run()

    def test_all_menu_handlers_exist(self):
        from app.ui.app import TerminalUI
        from app.ui.menu_system import MenuSystem
        with contextlib.redirect_stdout(io.StringIO()):
            ui = TerminalUI()
        self.assertIsInstance(ui.menu_system, MenuSystem)


if __name__ == '__main__':
    unittest.main()
