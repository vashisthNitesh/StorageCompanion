"""
Caps how many file transfers run at once in this process, separately for uploads and downloads.

Each transfer holds a server thread for as long as the person's connection takes to send or
receive the data. Without a cap, a few people uploading would occupy every thread and stall
browsing, sign-in and everything else; with one shared cap, uploads would crowd out thumbnails
and previews. Transfers beyond their cap get 503 + Retry-After right away and the app retries
them; the remaining threads stay free for quick requests.
"""
import threading

from django.conf import settings
from django.http import JsonResponse

UPLOAD = "upload"
DOWNLOAD = "download"
RETRY_AFTER_SECONDS = 3

_slots = {
    UPLOAD: threading.BoundedSemaphore(settings.UPLOAD_SLOTS),
    DOWNLOAD: threading.BoundedSemaphore(settings.DOWNLOAD_SLOTS),
}


def acquire(kind: str) -> bool:
    return _slots[kind].acquire(blocking=False)


def release(kind: str):
    _slots[kind].release()


def busy_response() -> JsonResponse:
    response = JsonResponse(
        {"error": "server_busy", "message": "Lots of transfers are running. This one will start in a moment.", "code": "SERVER_BUSY"},
        status=503,
    )
    response["Retry-After"] = str(RETRY_AFTER_SECONDS)
    # The request body may be unread; don't reuse this connection for another request.
    response["Connection"] = "close"
    return response


class ReleasingStream:
    """Streams an upstream body in chunks and frees the download slot when the response closes,
    whether or not it was ever read (Django calls close() on finished or abandoned responses)."""

    def __init__(self, upstream, chunk_size: int = 256 * 1024):
        self.upstream = upstream
        self.chunk_size = chunk_size
        self._released = False

    def __iter__(self):
        while True:
            chunk = self.upstream.read(self.chunk_size)
            if not chunk:
                break
            yield chunk

    def close(self):
        try:
            closer = getattr(self.upstream, "close", None)
            if closer:
                closer()
        except Exception:
            pass
        finally:
            if not self._released:
                self._released = True
                release(DOWNLOAD)
