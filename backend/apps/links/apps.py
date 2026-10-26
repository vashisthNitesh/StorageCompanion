from django.apps import AppConfig


class LinksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.links"
    # Not "sharing": that label belonged to an earlier, removed feature whose migrations may
    # still be recorded in existing databases.
    label = "links"
