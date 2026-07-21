import datetime
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from ..models import Topic, Settings, DailyDeck, TopicReview
from .common import _require_auth
from .problems import _make_problem

logger = logging.getLogger(__name__)


def _client_today(request):
    """The calendar day to treat as "today" for the requesting client.

    The deck resets at the start of each day, but "the day" means the user's
    local day — not the server's. The server clock runs in UTC (see
    settings.TIME_ZONE), so relying on `timezone.localdate()` would only roll
    the deck over at UTC midnight; a user ahead of UTC would keep seeing
    yesterday's (often finished) deck through their whole morning.

    The client sends its local date as `?today=YYYY-MM-DD`. We trust it: the
    only thing a user can affect by lying is when their own practice deck
    resets, which is harmless. If it's missing or malformed we fall back to the
    server's date so the endpoint still works (and existing callers/tests that
    don't send it keep their behaviour).
    """
    raw = request.GET.get("today")
    if raw:
        try:
            return datetime.date.fromisoformat(raw)
        except ValueError:
            logger.warning("Ignoring malformed 'today' param: %r", raw)
    return timezone.localdate()


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


def _select_deck_topics(user, today, count, exclude=()):
    """Pick up to `count` topics for today's deck, ordered by spaced repetition.

    This is the one place that decides *which* topics a deck is built from; the
    deck helpers all route through it so the ordering and de-duplication rules
    live in a single, testable spot. It reads the SM-2 schedule (each topic's
    `TopicReview.due_date`, written by the grading step) but never computes it —
    scheduling math lives in myapp.srs.

    Ordering combines two rules with a single sort on the effective due date:

    - Due first, most overdue first (Option A). A topic never reviewed has no
      `TopicReview` row; it's treated as due today (sorts alongside today's due
      topics), so new topics enter the rotation promptly.
    - Top up with the next-soonest (Option 2). When fewer topics are due than
      `count`, not-yet-due topics fill the remaining slots, soonest first —
      their future `due_date` sorts after everything already due, so they're
      only pulled in to avoid a short deck.

    `exclude` is a set/iterable of topic ids already in the deck; they're left
    out so top-up and tail-regeneration can't duplicate a topic (each topic
    appears at most once per day).

    Returns a list of Topic objects (length 0..count). It is empty *only* when
    the user has no usable topic selected outside `exclude` — never merely
    because nothing is due yet (the top-up guarantees a full deck while any
    topic is selected). Callers rely on that: an empty result means "no topics",
    not "nothing to review today".
    """
    if count <= 0:
        return []
    exclude = set(exclude)
    topics = list(
        Topic.objects.filter(selections__user=user, generator_name__isnull=False)
    )
    reviews = {
        r.topic_id: r
        for r in TopicReview.objects.filter(user=user, topic__in=topics)
    }

    def effective_due(topic):
        # No review row (never practiced) or no due date => due today, so new
        # topics sort in with today's due items rather than being deferred.
        review = reviews.get(topic.id)
        if review is None or review.due_date is None:
            return today
        return review.due_date

    candidates = [t for t in topics if t.id not in exclude]
    # Sort by effective due date; ties broken by id for a stable, deterministic
    # order (no reliance on DB row order).
    candidates.sort(key=lambda t: (effective_due(t), t.id))
    return candidates[:count]


def _get_or_create_today_deck(user, today):
    """Return the user's deck for today, creating a fresh one if none exists.

    `today` is the client's local calendar day (see `_client_today`), so the
    deck resets at the user's midnight rather than the server's UTC midnight.

    Any deck from a previous day (for this user) is discarded so a new day
    yields new problems. An existing deck that is shorter than the target
    `questions_per_day` is topped up (appending only, so progress is
    preserved). This heals a deck that was built before any topics were
    selected (empty) as well as one left short by a topic change earlier in
    the day — the latter is why the deck must never be reported as "finished"
    at a smaller size than the user's setting.
    """
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


def _grow_today_deck(user, count, today):
    """Grow today's deck to `count` problems if it's currently smaller.

    Appends freshly generated problems to the end so the student's progress
    (already-answered problems and `current_index`) is preserved. Never shrinks
    the deck: a smaller `count` is left to take effect when the next day's deck
    is built. Does nothing if there's no deck for today yet — that deck will be
    built at the new count on first access.
    """
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


def _regenerate_deck_tail(user, today):
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
    deck = _get_or_create_today_deck(request.user, _client_today(request))
    return JsonResponse(_deck_payload(request.user, deck))


@csrf_exempt
@require_http_methods(["POST"])
def advance_deck(request):
    """Move to the next problem in today's deck.

    Advancing only ever steps an *existing* deck forward — it must never build
    one. If we created-then-advanced here, a new day's deck (fresh at index 0)
    would be pushed to index 1 without the student answering anything, leaving
    them stranded on "2 of N" instead of card 1. This happens for real: the
    "correct answer" handler advances on a 900ms timer, so finishing a problem
    right before midnight fires the advance after the day has rolled over,
    making the day's first backend call an advance rather than a load.

    When there's no deck for today yet, treat the advance as a no-op and just
    report the freshly-built deck (get_or_create at index 0), so that stray
    advance lands the student on card 1.
    """
    auth = _require_auth(request)
    if auth:
        return auth
    today = _client_today(request)
    existing = DailyDeck.objects.filter(user=request.user, date=today).first()
    deck = _get_or_create_today_deck(request.user, today)
    if existing is not None and deck.current_index < len(deck.problems):
        deck.current_index += 1
        deck.save(update_fields=["current_index"])
        logger.debug(
            "User %s advanced deck to %d/%d",
            request.user.id, deck.current_index, len(deck.problems),
        )
    return JsonResponse(_deck_payload(request.user, deck))
