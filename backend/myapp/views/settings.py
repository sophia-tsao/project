import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from ..models import Settings
from .common import _require_auth
from .deck import _grow_today_deck

logger = logging.getLogger(__name__)


def _serialize_settings(settings):
    return {"language": settings.language, "questions_per_day": settings.questions_per_day}


@csrf_exempt
@require_http_methods(["GET", "PATCH"])
def settings_view(request):
    auth = _require_auth(request)
    if auth:
        return auth
    settings = Settings.load(request.user)
    if request.method == "PATCH":
        body = json.loads(request.body)
        if "language" in body:
            settings.language = body["language"]
        if "questions_per_day" in body:
            try:
                count = int(body["questions_per_day"])
            except (ValueError, TypeError):
                return JsonResponse({"error": "questions_per_day must be an integer"}, status=400)
            if count < 1:
                return JsonResponse({"error": "questions_per_day must be at least 1"}, status=400)
            settings.questions_per_day = count
        settings.save()
        logger.info(
            "User %s updated settings (language=%s, questions_per_day=%d)",
            request.user.id, settings.language, settings.questions_per_day,
        )
        # Apply a larger card count to today's deck immediately so the change
        # takes effect on save, not just tomorrow. We only ever grow the deck:
        # problems the student has already worked through stay put, and a
        # smaller count leaves today's deck untouched (it applies next day).
        _grow_today_deck(request.user, settings.questions_per_day)
    return JsonResponse(_serialize_settings(settings))
