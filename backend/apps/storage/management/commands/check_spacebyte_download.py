"""Diagnose why a SpaceByte-stored file can't be downloaded (live QA: upstream 403).

Usage: python manage.py check_spacebyte_download <node_id>
Prints whether a token is configured, the redirect/resolve result and the HTTP status of a
1-byte ranged download. Never prints the token.
"""
from django.core.management.base import BaseCommand, CommandError

from apps.storage.models import Node
from apps.storage.spacebyte import SpaceByteError, get_spacebyte_client


class Command(BaseCommand):
    help = "Check SpaceByte download access for a node."

    def add_arguments(self, parser):
        parser.add_argument("node_id")

    def handle(self, *args, **opts):
        node = Node.objects.filter(id=opts["node_id"]).first()
        if not node:
            raise CommandError("Node not found.")
        if not node.spacebyte_hash:
            raise CommandError("Node is not stored via SpaceByte file entries (no spacebyte_hash).")
        client = get_spacebyte_client()
        self.stdout.write(f"token configured: {client.is_configured}")
        self.stdout.write(f"entry hash: {node.spacebyte_hash}")
        resolved = client.resolve_direct_download_url(node.spacebyte_hash, timeout=10)
        self.stdout.write(f"resolved presigned URL: {'yes' if resolved else 'no'}")
        try:
            resp, code, headers = client.download_stream(node.spacebyte_hash, range_header="bytes=0-0", timeout=20)
            resp.close() if hasattr(resp, "close") else None
            self.stdout.write(self.style.SUCCESS(f"ranged download OK: HTTP {code}, Content-Range={headers.get('Content-Range')}"))
        except SpaceByteError as e:
            self.stdout.write(self.style.ERROR(f"download failed: HTTP {e.status_code}"))
            if e.status_code in (401, 403):
                self.stdout.write("-> token expired/revoked, or the entry belongs to another SpaceByte account/workspace.")
