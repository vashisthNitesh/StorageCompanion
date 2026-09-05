from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class QuotaExceededException(APIException):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = {
        "error": "quota_exceeded",
        "message": "Storage quota exceeded. Please upgrade your subscription plan to upload more files.",
        "code": "QUOTA_EXCEEDED"
    }
    default_code = "quota_exceeded"

    def __init__(self, detail=None, code=None, bytes_needed=None, bytes_remaining=None):
        if detail is None:
            detail = {
                "error": "quota_exceeded",
                "message": "Storage quota exceeded. Please upgrade your subscription plan to upload more files.",
                "code": "QUOTA_EXCEEDED",
                "bytes_needed": bytes_needed,
                "bytes_remaining": bytes_remaining,
            }
        super().__init__(detail, code)


class SubscriptionRequiredException(APIException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = {
        "error": "subscription_required",
        "message": "An active subscription is required to perform this action.",
        "code": "SUBSCRIPTION_REQUIRED"
    }
    default_code = "subscription_required"


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        if isinstance(response.data, dict) and "error" not in response.data:
            response.data = {
                "success": False,
                "error": response.data.get("detail", "Request failed"),
                "details": response.data,
                "status_code": response.status_code,
            }
    return response
