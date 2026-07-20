from .models import Course, Topic, UserTopicSelection, Settings, DailyDeck
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings as django_settings
from django.contrib.auth import login, logout, get_user_model
from django.utils import timezone
import mathgenerator
import random
import json
import logging

from .generators import LOCAL_GENERATORS

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

logger = logging.getLogger(__name__)

# Google signs tokens against its own clock. A small drift on the server clock
# is enough to make verify_oauth2_token reject every token with "Token used too
# early/late". Allow a modest tolerance so ordinary clock skew doesn't lock all
# users out.
GOOGLE_CLOCK_SKEW_SECONDS = 10


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

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


def _require_auth(request):
    """Return a 401 JsonResponse if not authenticated, else None."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    return None


# ---------------------------------------------------------------------------
# Courses & topics
# ---------------------------------------------------------------------------

def _course_is_selected(course, selected_ids):
    topic_ids = list(course.topics.values_list("id", flat=True))
    return bool(topic_ids) and all(tid in selected_ids for tid in topic_ids)


def view_courses(request):
    auth = _require_auth(request)
    if auth:
        return auth
    selected_ids = set(
        UserTopicSelection.objects.filter(user=request.user).values_list("topic_id", flat=True)
    )
    courses = []
    for course in Course.objects.all().prefetch_related("topics"):
        courses.append({
            "id": course.id,
            "course_name": course.course_name,
            "grade_level": course.grade_level,
            "is_selected": _course_is_selected(course, selected_ids),
        })
    return JsonResponse({"courses": courses})


def view_course_topics(request, courseID):
    auth = _require_auth(request)
    if auth:
        return auth
    # Returns topics for specific course, with this user's selection state.
    selected_ids = set(
        UserTopicSelection.objects.filter(user=request.user).values_list("topic_id", flat=True)
    )
    topics = []
    for topic in Course.objects.get(id=courseID).topics.all():
        topics.append({
            "id": topic.id,
            "topic_name": topic.topic_name,
            "course_id": topic.course_id,
            "generator_name": topic.generator_name,
            "is_selected": topic.id in selected_ids,
        })
    return JsonResponse({"topics": topics})


@csrf_exempt
@require_http_methods(["PATCH"])
def toggle_topic(request, topicID):
    auth = _require_auth(request)
    if auth:
        return auth
    try:
        topic = Topic.objects.get(id=topicID)
    except Topic.DoesNotExist:
        return JsonResponse({"error": "Topic not found"}, status=404)
    body = json.loads(request.body)
    is_selected = body["is_selected"]
    if is_selected:
        UserTopicSelection.objects.get_or_create(user=request.user, topic=topic)
    else:
        UserTopicSelection.objects.filter(user=request.user, topic=topic).delete()
    logger.info(
        "User %s %s topic %s", request.user.id,
        "selected" if is_selected else "deselected", topic.id,
    )
    # Apply the topic change to today's deck immediately (see helper docstring).
    _regenerate_deck_tail(request.user)
    return JsonResponse({"id": topic.id, "is_selected": is_selected})


@csrf_exempt
@require_http_methods(["PATCH"])
def set_course_topics_selected(request, courseID):
    auth = _require_auth(request)
    if auth:
        return auth
    try:
        course = Course.objects.get(id=courseID)
    except Course.DoesNotExist:
        return JsonResponse({"error": "Course not found"}, status=404)
    body = json.loads(request.body)
    new_value = body["is_selected"]
    topics = course.topics.all()
    if new_value:
        UserTopicSelection.objects.bulk_create(
            [UserTopicSelection(user=request.user, topic=t) for t in topics],
            ignore_conflicts=True,
        )
    else:
        UserTopicSelection.objects.filter(user=request.user, topic__in=topics).delete()
    logger.info(
        "User %s %s all %d topics in course %s", request.user.id,
        "selected" if new_value else "deselected", len(topics), courseID,
    )
    # Apply the topic change to today's deck immediately (see helper docstring).
    _regenerate_deck_tail(request.user)
    return JsonResponse({"course_id": courseID, "is_selected": new_value})


# ---------------------------------------------------------------------------
# Problem generation
# ---------------------------------------------------------------------------

def _make_problem(user):
    """Generate a single problem from the user's currently selected topics.

    Returns a dict with 'problem' and 'solution', or None if no topics are
    selected.
    """
    generators = list(
        Topic.objects.filter(selections__user=user)
        .exclude(generator_name__isnull=True)
        .values_list("generator_name", flat=True)
    )
    if not generators:
        return None
    name = random.choice(generators)
    # Prefer our own generators, then fall back to the mathgenerator library.
    generator = LOCAL_GENERATORS.get(name) or getattr(mathgenerator, name, None)
    if generator is None:
        # The stored generator name isn't a real generator (e.g. renamed or
        # removed by a library upgrade). Treat it as "no problem available"
        # rather than 500-ing the student. The contract test in
        # test_generators.py exists to catch this before it ships.
        logger.warning("No generator found for name %r; skipping problem", name)
        return None
    problem, solution = generator()

    # Strip the surrounding LaTeX '$' delimiters so every solution is returned
    # consistently, whether it's an integer, a decimal, or a symbolic answer.
    sol_str = str(solution).strip().replace('$', '').strip()
    try:
        sol_float = float(sol_str)
        if '.' in sol_str:
            rounded = round(sol_float, 3)
            rounded_str = str(rounded)
            if rounded_str != sol_str:
                problem = problem.rstrip() + " Round to the nearest thousandth if necessary."
            sol_str = rounded_str
    except (ValueError, TypeError):
        pass

    return {"problem": problem, "solution": sol_str}


def generate_problem(request):
    auth = _require_auth(request)
    if auth:
        return auth
    result = _make_problem(request.user)
    if result is None:
        return JsonResponse({"no_topics": True})
    return JsonResponse(result)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Daily deck
# ---------------------------------------------------------------------------

def _build_deck(user, count):
    """Generate up to `count` problems. Returns a list (possibly empty)."""
    problems = []
    for _ in range(count):
        problem = _make_problem(user)
        if problem is None:
            break
        problems.append(problem)
    return problems


def _has_topics(user):
    """True if the user currently has at least one usable topic selected."""
    return Topic.objects.filter(
        selections__user=user, generator_name__isnull=False
    ).exists()


def _get_or_create_today_deck(user):
    """Return the user's deck for today, creating a fresh one if none exists.

    Any deck from a previous day (for this user) is discarded so a new day
    yields new problems. An existing deck that is shorter than the target
    `questions_per_day` is topped up (appending only, so progress is
    preserved). This heals a deck that was built before any topics were
    selected (empty) as well as one left short by a topic change earlier in
    the day — the latter is why the deck must never be reported as "finished"
    at a smaller size than the user's setting.
    """
    today = timezone.localdate()
    deck = DailyDeck.objects.filter(user=user, date=today).first()
    settings = Settings.load(user)
    if deck is None:
        # A new day: clear out this user's stale decks and build a fresh one.
        DailyDeck.objects.filter(user=user).exclude(date=today).delete()
        problems = _build_deck(user, settings.questions_per_day)
        logger.info(
            "Built new deck for user %s with %d/%d problems",
            user.id, len(problems), settings.questions_per_day,
        )
        return DailyDeck.objects.create(
            user=user, date=today, problems=problems, current_index=0
        )
    missing = settings.questions_per_day - len(deck.problems)
    if missing > 0:
        extra = _build_deck(user, missing)
        if extra:
            deck.problems = deck.problems + extra
            deck.save(update_fields=["problems"])
            logger.info(
                "Topped up deck for user %s by %d problems (now %d)",
                user.id, len(extra), len(deck.problems),
            )
    return deck


def _grow_today_deck(user, count):
    """Grow today's deck to `count` problems if it's currently smaller.

    Appends freshly generated problems to the end so the student's progress
    (already-answered problems and `current_index`) is preserved. Never shrinks
    the deck: a smaller `count` is left to take effect when the next day's deck
    is built. Does nothing if there's no deck for today yet — that deck will be
    built at the new count on first access.
    """
    today = timezone.localdate()
    deck = DailyDeck.objects.filter(user=user, date=today).first()
    if deck is None:
        return
    missing = count - len(deck.problems)
    if missing <= 0:
        return
    extra = _build_deck(user, missing)
    if extra:
        deck.problems = deck.problems + extra
        deck.save(update_fields=["problems"])
        logger.info(
            "Grew deck for user %s to %d problems (target %d)",
            user.id, len(deck.problems), count,
        )


def _regenerate_deck_tail(user):
    """Rebuild today's not-yet-answered problems from the current topic set.

    Problems the student has already worked through (everything before
    `current_index`) are kept; the remaining cards are regenerated from the
    topics currently selected, refilling the deck back up to the target count
    (`questions_per_day`) and preserving the student's position. This lets a
    topic toggle take effect immediately — stored problems only carry their
    text/solution, not the topic they came from, so an individual topic's
    cards can't be surgically removed; we regenerate the tail instead.

    The tail size is derived from the target count rather than the current
    deck length, so refilling always aims for `questions_per_day`.

    Does nothing if there's no deck for today yet (it'll be built from the
    current topics on first access), if the student has already answered at
    least the target number of problems today, or if no topics are currently
    selected. That last case matters: swapping topic sets is two steps
    (deselect the old, select the new), and in between nothing is selected.
    Regenerating then would produce an empty tail; writing it back would
    truncate the deck down to just the answered cards and strand the student
    on an already-"finished" deck. Leaving the deck untouched lets the
    following selection rebuild the tail properly.
    """
    today = timezone.localdate()
    deck = DailyDeck.objects.filter(user=user, date=today).first()
    if deck is None:
        return
    answered = deck.current_index
    target = Settings.load(user).questions_per_day
    remaining = target - answered
    if remaining <= 0:
        return
    new_tail = _build_deck(user, remaining)
    if not new_tail:
        # No topics currently selected — can't regenerate. Preserve the deck
        # rather than truncating away its unanswered tail.
        logger.debug(
            "Skipped deck tail regeneration for user %s: no problems generated",
            user.id,
        )
        return
    deck.problems = deck.problems[:answered] + new_tail
    deck.save(update_fields=["problems"])
    logger.info(
        "Regenerated deck tail for user %s: kept %d answered, %d new",
        user.id, answered, len(new_tail),
    )


def _deck_payload(user, deck):
    # "No topics" is driven by the live selection, not the deck contents, so
    # deselecting every topic shows the "pick a topic" screen immediately even
    # if the deck still holds problems from before the change.
    if not _has_topics(user):
        return {"no_topics": True}
    # Present the deck capped to the current setting. Growing the count is
    # handled when the deck is loaded (extra cards are appended); shrinking it
    # is applied here at display time, so a smaller `questions_per_day` takes
    # effect immediately rather than next day. We only cap the view — the extra
    # cards stay stored, so raising the count back up restores them. Without
    # this cap, reducing the count after answering more than the new total
    # would keep showing the old (larger) deck instead of "finished".
    target = Settings.load(user).questions_per_day
    total = min(len(deck.problems), target)
    if total == 0:
        return {"no_topics": True}
    if deck.current_index >= total:
        return {"completed": True, "total": total}
    current = deck.problems[deck.current_index]
    return {
        "problem": current["problem"],
        "solution": current["solution"],
        "current_number": deck.current_index + 1,
        "total": total,
    }


@csrf_exempt
@require_http_methods(["GET"])
def get_deck(request):
    auth = _require_auth(request)
    if auth:
        return auth
    deck = _get_or_create_today_deck(request.user)
    return JsonResponse(_deck_payload(request.user, deck))


@csrf_exempt
@require_http_methods(["POST"])
def advance_deck(request):
    """Move to the next problem in today's deck."""
    auth = _require_auth(request)
    if auth:
        return auth
    deck = _get_or_create_today_deck(request.user)
    if deck.current_index < len(deck.problems):
        deck.current_index += 1
        deck.save(update_fields=["current_index"])
        logger.debug(
            "User %s advanced deck to %d/%d",
            request.user.id, deck.current_index, len(deck.problems),
        )
    return JsonResponse(_deck_payload(request.user, deck))
