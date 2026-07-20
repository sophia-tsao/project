import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from ..models import Topic, Settings, DailyDeck
from .common import _require_auth
from .problems import _make_problem

logger = logging.getLogger(__name__)


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
