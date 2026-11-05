from django.db import migrations


def ensure_notification_queued_column(apps, schema_editor):
    model = apps.get_model("monitoring", "AlertEvent")
    connection = schema_editor.connection
    table_name = model._meta.db_table
    field = model._meta.get_field("last_notification_queued_at")

    with connection.cursor() as cursor:
        if table_name not in connection.introspection.table_names(cursor):
            raise RuntimeError(
                f"Expected monitoring table {table_name!r} is missing."
            )
        columns = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, table_name
            )
        }

    if field.column not in columns:
        schema_editor.add_field(model, field)


class Migration(migrations.Migration):
    dependencies = [
        ("monitoring", "0004_alertevent_last_notification_queued_at"),
    ]

    operations = [
        migrations.RunPython(
            ensure_notification_queued_column,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
