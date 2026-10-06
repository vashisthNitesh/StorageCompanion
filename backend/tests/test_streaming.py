import asyncio

from django.test import AsyncRequestFactory, RequestFactory

from apps.common.streaming import stream_iterator


def test_wsgi_keeps_sync_iterator():
    src = iter([b"a", b"b"])
    assert stream_iterator(RequestFactory().get("/"), src) is src


def test_asgi_streams_lazily_one_chunk_at_a_time():
    pulled = []

    def source():
        for i in range(1000):
            pulled.append(i)
            yield b"x" * 10

    it = stream_iterator(AsyncRequestFactory().get("/"), source())
    assert hasattr(it, "__aiter__")

    async def first_chunk():
        agen = it.__aiter__()
        chunk = await agen.__anext__()
        await agen.aclose()
        return chunk

    assert asyncio.run(first_chunk()) == b"x" * 10
    # Django's fallback would have materialized all 1000 chunks before sending the first one
    assert len(pulled) == 1


def test_upload_endpoints_use_scoped_upload_throttle_not_daily_user_quota():
    from rest_framework.throttling import ScopedRateThrottle

    from apps.storage.views import UploadCompleteView, UploadInitView, UploadPartRelayView

    for view in (UploadInitView, UploadPartRelayView, UploadCompleteView):
        assert view.throttle_classes == [ScopedRateThrottle]
        assert view.throttle_scope == "uploads"


def test_webhook_is_not_throttled():
    from apps.billing.views import RazorpayWebhookView

    assert RazorpayWebhookView.throttle_classes == []
