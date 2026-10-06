from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed SmartSpace Data plans (safe wrapper, no demo users or files created)."

    def handle(self, *args, **options):
        self.stdout.write("Running plan configuration...")
        call_command("seed_plans")
