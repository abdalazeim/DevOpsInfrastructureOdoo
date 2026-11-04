from dataclasses import dataclass

from django.test import SimpleTestCase

from infrastructure_engine.core.engine import InfrastructureEngine, OperationRejected
from infrastructure_engine.security.command_validator import (
    InvalidOperationParameters, validate_structured_parameters,
)
from infrastructure_engine.security.execution_policy import ExecutionPolicy, PolicyViolation


class InfrastructureEnginePolicyTests(SimpleTestCase):
    def test_only_registered_operation_codes_are_accepted(self):
        with self.assertRaises(OperationRejected) as raised:
            InfrastructureEngine.execute(
                "system.run_command", target_id=1, actor=None, parameters={"command": "id"},
            )
        self.assertEqual(raised.exception.status_code, 404)

    def test_structured_parameter_validation_rejects_unknown_shell_payload(self):
        with self.assertRaises(InvalidOperationParameters):
            validate_structured_parameters({"command": "uname -a"}, allowed_keys=())

    def test_structured_parameter_validation_rejects_nul_and_oversize_values(self):
        with self.assertRaises(InvalidOperationParameters):
            validate_structured_parameters({"path": "bad\x00path"}, allowed_keys=("path",))
        with self.assertRaises(InvalidOperationParameters):
            validate_structured_parameters({"path": "x" * 5000}, allowed_keys=("path",))

    def test_mutating_operation_cannot_bypass_task_dispatch(self):
        @dataclass
        class MutationSpec:
            mutating: bool = True
            requires_confirmation: bool = True

        with self.assertRaises(PolicyViolation):
            ExecutionPolicy.authorize(MutationSpec(), confirmation=True, task_dispatch_enabled=False)

    def test_confirmation_requirement_is_enforced_by_policy(self):
        @dataclass
        class ConfirmedOperation:
            mutating: bool = False
            requires_confirmation: bool = True

        with self.assertRaises(PolicyViolation):
            ExecutionPolicy.authorize(ConfirmedOperation(), confirmation=False)
