from django.http import JsonResponse


def health(request):
    """Unauthenticated, unthrottled liveness probe for the hosting platform."""
    return JsonResponse({"status": "ok"})
