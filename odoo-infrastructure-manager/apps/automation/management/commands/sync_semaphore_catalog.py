from django.core.management.base import BaseCommand, CommandError

from apps.automation.models import ApprovedTaskTemplate
from apps.automation.services import SemaphoreClient, SemaphoreError


class Command(BaseCommand):
    help = "Import Semaphore projects and templates into the local catalog as disabled pending admin review."

    def handle(self, *args, **options):
        client = SemaphoreClient()
        try:
            projects = client.list_projects()
            created = updated = 0
            for project in projects:
                project_id = _positive_int(project.get("id"))
                if project_id is None:
                    continue
                for remote in client.list_templates(project_id):
                    template_id = _positive_int(remote.get("id"))
                    if template_id is None:
                        continue
                    name = str(remote.get("name") or f"Semaphore template {template_id}")[:120]
                    description = str(remote.get("description") or "Imported from Semaphore; review scope and category before enabling.")[:4000]
                    obj, was_created = ApprovedTaskTemplate.objects.get_or_create(
                        project_id=project_id,
                        template_id=template_id,
                        defaults={
                            "name": name,
                            "description": description,
                            "category": ApprovedTaskTemplate.Category.MAINTENANCE,
                            "enabled": False,
                            "read_only": True,
                            "requires_confirmation": True,
                        },
                    )
                    if was_created:
                        created += 1
                    elif not obj.enabled:
                        obj.name = name
                        obj.description = description
                        obj.save(update_fields=["name", "description"])
                        updated += 1
            self.stdout.write(self.style.SUCCESS(
                f"Imported {created} new and refreshed {updated} disabled or pending-review template(s)."
            ))
        except SemaphoreError as exc:
            raise CommandError(str(exc)) from exc


def _positive_int(value):
    try:
        parsed = int(value)
        return parsed if parsed > 0 else None
    except (TypeError, ValueError):
        return None
