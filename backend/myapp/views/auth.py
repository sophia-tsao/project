import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings as django_settings
from django.contrib.auth import login, logout, get_user_model

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

logger = logging.getLogger(__name__)

# Google signs tokens against its own clock. A small drift on the server clock
# is enough to make verify_oauth2_token reject every token with "Token used too
# early/late". Allow a modest tolerance so ordinary clock skew doesn't lock all
# users out.
GOOGLE_CLOCK_SKEW_SECONDS = 10


def _serialize_user(user):
    return {
        "id": user.id,
        "email": user.email,
        "name": (user.get_full_name() or user.username or user.email),
    }


@csrf_exempt
@require_http_methods(["GET"])
def me(request):
    """Return the current user, or authenticated=False if not logged in."""
    if request.user.is_authenticated:
        return JsonResponse({"authenticated": True, "user": _serialize_user(request.user)})
    return JsonResponse({"authenticated": False})


@csrf_exempt
@require_http_methods(["POST"])
def google_login(request):
    """Verify a Google ID token and log the user in, creating them if needed."""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid request body"}, status=400)

    token = body.get("credential")
    if not token:
        return JsonResponse({"error": "Missing credential"}, status=400)

    client_id = getattr(django_settings, "GOOGLE_OAUTH_CLIENT_ID", None)
    if not client_id:
        return JsonResponse({"error": "Google login is not configured on the server"}, status=500)

    try:
        idinfo = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            client_id,
            clock_skew_in_seconds=GOOGLE_CLOCK_SKEW_SECONDS,
        )
    except ValueError as exc:
        # Surface the underlying reason (bad audience, expiry, clock skew, ...)
        # to the logs; the client only gets a generic message.
        logger.warning("Google token verification failed: %s", exc)
        return JsonResponse({"error": "Invalid Google token"}, status=401)

    email = idinfo.get("email")
    if not email or not idinfo.get("email_verified", False):
        logger.warning("Rejected Google login: email missing or unverified")
        return JsonResponse({"error": "Google account email is not verified"}, status=401)

    User = get_user_model()
    # Use the Google subject as the stable username; fall back to email.
    google_sub = idinfo.get("sub")
    user, created = User.objects.get_or_create(
        username=google_sub or email,
        defaults={
            "email": email,
            "first_name": idinfo.get("given_name", ""),
            "last_name": idinfo.get("family_name", ""),
        },
    )
    # Keep email/name fresh on returning users.
    if not created and user.email != email:
        user.email = email
        user.save(update_fields=["email"])

    login(request, user)
    logger.info(
        "Google login succeeded for user %s (%s account)",
        user.id, "new" if created else "existing",
    )
    return JsonResponse({"authenticated": True, "user": _serialize_user(user)})


@csrf_exempt
@require_http_methods(["POST"])
def logout_view(request):
    user_id = request.user.id if request.user.is_authenticated else None
    logout(request)
    logger.info("User %s logged out", user_id)
    return JsonResponse({"ok": True})


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_account(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Not authenticated"}, status=401)
    user = request.user
    user_id = user.id
    logout(request)
    user.delete()  # Cascades to selections, settings, and decks.
    logger.info("Deleted account for user %s and all associated data", user_id)
    return JsonResponse({"ok": True})
