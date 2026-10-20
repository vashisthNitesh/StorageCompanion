from django.db import migrations


def drop_sharing_table(apps, schema_editor):
    """The link/user sharing feature was removed; drop its table so its foreign keys
    to users and nodes cannot block deleting either."""
    cascade = " CASCADE" if schema_editor.connection.vendor == "postgresql" else ""
    schema_editor.execute(f"DROP TABLE IF EXISTS sharing_share{cascade}")


class Migration(migrations.Migration):

    dependencies = [
        ("storage", "0004_upload_received_parts_alter_upload_part_size"),
    ]

    operations = [
        migrations.RunPython(drop_sharing_table, migrations.RunPython.noop),
    ]
