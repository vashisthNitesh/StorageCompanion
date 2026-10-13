from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("storage", "0002_fileversion_spacebyte_file_name_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="fileversion",
            name="part_size",
            field=models.IntegerField(default=0),
        ),
    ]
