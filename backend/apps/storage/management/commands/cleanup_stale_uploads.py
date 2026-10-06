"""Abort multipart uploads that were started but never completed (abandoned tabs, crashes).

Incomplete multipart uploads keep their parts (and cost) at the provider until aborted.
Usage: python manage.py cleanup_stale_uploads [--hours 48] [--dry-run]   (schedule daily)
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.storage.models import Upload
from apps.storage.services import abort_multipart_upload


class Command(BaseCommand):
    help = "Abort initiated/uploading multipart uploads older than --hours."

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=48)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        cutoff = timezone.now() - timedelta(hours=opts["hours"])
        stale = Upload.objects.filter(
            status__in=[Upload.STATUS_INITIATED, Upload.STATUS_UPLOADING], created_at__lt=cutoff
        ).select_related("user")
        count = 0
        for upload in stale:
            count += 1
            if not opts["dry_run"]:
                abort_multipart_upload(upload.id, upload.user)
        verb = "Would abort" if opts["dry_run"] else "Aborted"
        self.stdout.write(self.style.SUCCESS(f"{verb} {count} stale upload(s) older than {opts['hours']}h"))
