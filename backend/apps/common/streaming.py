"""Streaming helpers that work under both WSGI and ASGI.

Production runs Django under ASGI (gunicorn + UvicornWorker). Django's ASGI handler cannot
iterate a *synchronous* iterator lazily: StreamingHttpResponse.__aiter__ falls back to
`sync_to_async(list)(iterator)`, i.e. it reads the ENTIRE file into memory before sending the
first byte ("StreamingHttpResponse must consume synchronous iterators..."). On a 512 MB
instance a large download never starts (worker OOM / timeout). Under ASGI we therefore hand
Django an async iterator that pulls one chunk at a time from the sync source in a thread.
"""
from asgiref.sync import sync_to_async
from django.core.handlers.asgi import ASGIRequest

_SENTINEL = object()


def _is_asgi(request) -> bool:
    raw = getattr(request, "_request", request)  # DRF Request wraps the Django HttpRequest
    return isinstance(raw, ASGIRequest)


def stream_iterator(request, sync_iterable):
    """Return an iterator suitable for StreamingHttpResponse for the current server type."""
    if not _is_asgi(request):
        return sync_iterable

    iterator = iter(sync_iterable)

    def _next():
        return next(iterator, _SENTINEL)

    def _close():
        close = getattr(iterator, "close", None)
        if callable(close):
            close()

    async def agen():
        try:
            while True:
                chunk = await sync_to_async(_next, thread_sensitive=False)()
                if chunk is _SENTINEL:
                    break
                yield chunk
        finally:
            await sync_to_async(_close, thread_sensitive=False)()

    return agen()
