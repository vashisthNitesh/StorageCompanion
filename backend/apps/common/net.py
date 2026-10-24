from django.conf import settings


def get_client_ip(request) -> str | None:
    """
    The visitor's IP address.

    In production every request reaches Render through Cloudflare, which sets CF-Connecting-IP to
    the real client address (replacing any value the client sent), so that header is trusted first
    (CLIENT_IP_HEADER; set it to "" when not behind Cloudflare). X-Forwarded-For's first entry is
    whatever the client wrote, so it's only a fallback; with NUM_PROXIES set, the address appended
    by the outermost trusted proxy is used instead.
    """
    header = getattr(settings, "CLIENT_IP_HEADER", "")
    if header:
        value = request.META.get(header, "").split(",")[0].strip()
        if value:
            return value
    xff = [a.strip() for a in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if a.strip()]
    if xff:
        proxies = settings.REST_FRAMEWORK.get("NUM_PROXIES") or 0
        return xff[-min(proxies, len(xff))] if proxies else xff[0]
    return request.META.get("REMOTE_ADDR")
