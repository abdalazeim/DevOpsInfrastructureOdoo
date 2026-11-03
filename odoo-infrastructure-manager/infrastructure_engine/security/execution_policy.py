"""Policy checks shared by registered infrastructure operations."""


class PolicyViolation(Exception):
    pass


class ExecutionPolicy:
    @staticmethod
    def authorize(spec, *, confirmation=None, task_dispatch_enabled=False):
        if spec.mutating and not task_dispatch_enabled:
            raise PolicyViolation("Task dispatch is not enabled for this operation.")
        if spec.requires_confirmation and confirmation is not True:
            raise PolicyViolation("Explicit confirmation is required.")
