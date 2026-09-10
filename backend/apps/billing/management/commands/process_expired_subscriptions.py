from django.core.management.base import BaseCommand
from apps.billing.services import process_expired_subscriptions


class Command(BaseCommand):
    help = "Check and transition subscriptions past period_end or grace window, and reclaim unused pool capacity."

    def handle(self, *args, **options):
        self.stdout.write("Processing subscription lifecycle transitions...")
        summary = process_expired_subscriptions()
        self.stdout.write(
            self.style.SUCCESS(
                f"Completed: "
                f"{summary['transitioned_to_grace_period']} entered grace period, "
                f"{summary['transitioned_to_canceled']} canceled at period end, "
                f"{summary['transitioned_to_expired']} expired."
            )
        )
