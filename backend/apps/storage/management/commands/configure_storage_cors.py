"""Configure CORS on the app's own S3/R2 bucket so browsers can upload/download directly.

Live QA: direct part uploads failed with "No 'Access-Control-Allow-Origin' header" because the
bucket had no CORS rule for the app origin. The browser also needs ETag exposed to complete
multipart uploads. Usage:

    python manage.py configure_storage_cors --origin https://storagecompanion.onrender.com [--dry-run]

Note: this only applies to the bucket configured via S3_* settings. Buckets owned by SpaceByte
(storage.spacebyte.cloud) must be configured by SpaceByte; until then the client relays parts
through the backend automatically.
"""
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.storage.services import get_s3_client


def build_cors_rules(origins: list[str]) -> dict:
    return {
        "CORSRules": [
            {
                "AllowedOrigins": origins,
                "AllowedMethods": ["GET", "PUT", "HEAD"],
                "AllowedHeaders": ["*"],
                "ExposeHeaders": ["ETag", "Content-Length", "Content-Range", "Accept-Ranges"],
                "MaxAgeSeconds": 3600,
            }
        ]
    }


class Command(BaseCommand):
    help = "Apply a CORS policy (PUT/GET from the app origin, ETag exposed) to the S3/R2 bucket."

    def add_arguments(self, parser):
        parser.add_argument("--origin", action="append", required=True, help="Allowed origin (repeatable)")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        origins = [o.rstrip("/") for o in opts["origin"]]
        if any(o == "*" for o in origins):
            raise CommandError("Refusing to allow '*'; pass the exact app origin(s).")
        rules = build_cors_rules(origins)
        if opts["dry_run"]:
            self.stdout.write(json.dumps(rules, indent=2))
            return
        s3 = get_s3_client()
        s3.put_bucket_cors(Bucket=settings.S3_BUCKET_NAME, CORSConfiguration=rules)
        self.stdout.write(self.style.SUCCESS(f"CORS applied to bucket {settings.S3_BUCKET_NAME} for {', '.join(origins)}"))
