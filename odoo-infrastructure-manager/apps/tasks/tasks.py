"""Celery autodiscovery module; database state remains the task source of truth."""
try:
    from config.celery import app
except ModuleNotFoundError as exc:
    if exc.name != "celery":
        raise
    app = None


if app is not None:
    @app.task(name="infrastructure.execute_task", ignore_result=True)
    def execute_infrastructure_task(task_id):
        from apps.tasks.services.runner import run_infrastructure_task

        return run_infrastructure_task(task_id)
else:
    def execute_infrastructure_task(task_id):
        raise RuntimeError("Celery is not installed; task dispatch is unavailable.")
