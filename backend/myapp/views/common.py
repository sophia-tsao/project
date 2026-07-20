from django.http import JsonResponse


def _require_auth(request):
    """Return a 401 JsonResponse if not authenticated, else None."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    return None
