import datetime
import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from ..models import Topic, Settings, DailyDeck, TopicReview, DailyTopicGrade
from .common import _require_auth
from .problems import _make_problem_for_topic
from .. import srs

logger = logging.getLogger(__name__)

# Map an answer outcome to an SM-2 quality grade (0-5). The client reports which
# of these happened when it advances past a card.
#   correct_first  -> 5  (recalled cleanly)
#   correct_second -> 3  (correct, but only on the second attempt: hard)
#   incorrect      -> 1  (failed both attempts: a lapse)
_OUTCOME_QUALITY = {
    "correct_first": 5,
    "correct_second": 3,
    "incorrect": 1,
}


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


def _has_topics(user):
    """True if the user currently has at least one usable topic selected."""
    return Topic.objects.filter(
        selections__user=user, generator_name__isnull=False
    ).exists()


def _effective_due_dates(user, topics, today):
    """Map each topic id to its effective SM-2 due date.

    Reads each topic's `TopicReview.due_date` (written by the grading step) but
    never computes it — scheduling math lives in myapp.srs. A topic never
    practiced has no `TopicReview` row (or a null `due_date`); it's treated as
    due *today*, so new topics enter the rotation promptly rather than being
    deferred. Shared by `_ordered_topics` (ordering) and `_weighted_topic_plan`
    (how many slots a topic gets), so both read one consistent notion of "due".
    """
    reviews = {
        r.topic_id: r
        for r in TopicReview.objects.filter(user=user, topic__in=topics)
    }
    due = {}
    for topic in topics:
        review = reviews.get(topic.id)
        if review is None or review.due_date is None:
            due[topic.id] = today
        else:
            due[topic.id] = review.due_date
    return due


def _ordered_topics(user, today):
    """The user's selected, usable topics ordered by spaced-repetition priority.

    This is the one place that decides the *order* topics are reviewed in; the
    deck helpers route through it so the ordering rule lives in a single,
    testable spot.

    A single sort on each topic's effective due date yields the whole policy:

    - Due first, most overdue first (Option A). A topic never reviewed is
      treated as due today (see `_effective_due_dates`), so new topics enter the
      rotation promptly rather than being deferred.
    - Next-soonest after that (Option 2). Not-yet-due topics have a future
      `due_date`, so they sort after everything already due — they're only
      reached once the due topics run out.

    Ties break by topic id for a stable, deterministic order (no reliance on DB
    row order). Returns every usable selected topic (a Topic list, possibly
    empty); callers slice or cycle it to the size they need.
    """
    topics = list(
        Topic.objects.filter(selections__user=user, generator_name__isnull=False)
    )
    due = _effective_due_dates(user, topics, today)
    topics.sort(key=lambda t: (due[t.id], t.id))
    return topics


def _select_deck_topics(user, today, count, exclude=()):
    """The next `count` distinct topics to review, in due order, skipping `exclude`.

    A thin slice over `_ordered_topics`. `exclude` is a set/iterable of topic
    ids already in the deck, so callers topping up a deck get *fresh* topics
    first (variety before repeats). Returns 0..count Topic objects; empty only
    when the user has no usable topic selected outside `exclude`.
    """
    if count <= 0:
        return []
    exclude = set(exclude)
    return [t for t in _ordered_topics(user, today) if t.id not in exclude][:count]


def _deck_topic_ids(deck):
    """Source topic ids of a deck's stored problems, skipping any that lack one.

    Problems stored before topic attribution was added (or by a client that
    predates it) have no `topic_id`; they're simply omitted rather than crashing
    a top-up. The result is used only to prefer fresh topics when topping up, so
    a missing id degrades to "might repeat this topic", never an error.
    """
    return [p["topic_id"] for p in deck.problems if "topic_id" in p]


def _due_weight(due_date, today):
    """How many deck slots a topic should compete for, by how overdue it is.

    This is the SM-2 signal expressed as *dose within a day* rather than only as
    ordering: a topic that's due (or overdue) should occupy more of today's deck
    than one whose next review is still days away. The weight rises with
    overdueness and falls as the due date recedes into the future, and is
    continuous at "due today" (both branches give 1):

    - due today or overdue by N days -> weight N + 1 (1, 2, 3, ...)
    - due in N days                  -> weight 1/(N + 1) (1/2, 1/3, ...)

    Weights are relative; only their ratios matter to the allocation below.
    """
    days_overdue = (today - due_date).days
    if days_overdue >= 0:
        return float(days_overdue + 1)
    return 1.0 / (1 - days_overdue)


def _weighted_slot_counts(rotation, due, count, today):
    """Split `count` deck slots across `rotation` topics, weighted by due priority.

    Every topic gets one slot first (a variety floor: every selected topic still
    appears in the deck), then the *remaining* slots are handed out in proportion
    to each topic's `_due_weight`, so an overdue topic takes a larger share than
    one that isn't due yet. The leftover from integer rounding goes to the
    largest fractional remainders (the standard largest-remainder method), which
    keeps the allocation deterministic and summing to exactly `count`.

    When there are at least `count` topics no repeats are needed, so the first
    `count` (already in due order) simply get one slot each and weighting is moot.
    Returns {topic_id: slot_count} summing to min(count, len(rotation)*...) —
    exactly `count` whenever any topic is present.
    """
    n = len(rotation)
    if n >= count:
        return {t.id: 1 for t in rotation[:count]}

    remaining = count - n  # slots left after the one-each variety floor
    weights = {t.id: _due_weight(due[t.id], today) for t in rotation}
    total = sum(weights.values())
    exact = {t.id: remaining * weights[t.id] / total for t in rotation}
    floors = {tid: int(v) for tid, v in exact.items()}
    leftover = remaining - sum(floors.values())
    # Hand the rounding leftover to the largest remainders; stable sort keeps
    # ties in due order (rotation order), so the allocation is deterministic.
    by_remainder = sorted(
        rotation, key=lambda t: exact[t.id] - floors[t.id], reverse=True
    )
    for t in by_remainder[:leftover]:
        floors[t.id] += 1
    return {t.id: 1 + floors[t.id] for t in rotation}


def _generate_problems(user, count, today, existing=()):
    """Generate exactly `count` problems for the deck, weighted by due priority.

    Distinct topics come first, most-due first (so a fresh or topped-up deck has
    as much variety as the user's topic set allows). When there are fewer usable
    topics than `count`, topics repeat to fill the deck — but not evenly: slots
    are allocated by `_weighted_slot_counts`, so a topic that's due or overdue
    occupies more of the deck than one whose next review is still days out. This
    keeps the deck full (SM-2 alone would leave a 2-topic user with one due card)
    while still reflecting SM-2's core signal: practice the due thing more.
    `existing` is the topic ids already in the deck; those topics are placed last
    within the rotation, so a top-up adds new topics before repeating any.

    Each problem records its source topic id (see `_make_problem_for_topic`), so
    a repeated topic yields a different generated problem but is still
    attributable for scheduling. Returns a list of up to `count` problems; fewer
    only if no topics are usable (empty) or every candidate topic's generator is
    broken.
    """
    if count <= 0:
        return []
    ordered = _ordered_topics(user, today)
    if not ordered:
        return []
    # Prefer topics not already in the deck, preserving due order within each
    # group, so top-ups add variety before repeating.
    existing = set(existing)
    fresh = [t for t in ordered if t.id not in existing]
    repeats = [t for t in ordered if t.id in existing]
    rotation = fresh + repeats

    due = _effective_due_dates(user, rotation, today)
    counts = _weighted_slot_counts(rotation, due, count, today)
    # Emit the planned slots in due order, one topic per pass, so a topic's
    # repeats are spread through the deck and the most-due topic leads.
    sequence = []
    left = dict(counts)
    while len(sequence) < sum(counts.values()):
        for topic in rotation:
            if left.get(topic.id, 0) > 0:
                sequence.append(topic)
                left[topic.id] -= 1

    problems = []
    broken = set()
    for planned in sequence:
        # Try the planned topic; if its generator is broken, fall back to any
        # other working topic so one dud skews toward the rest rather than
        # short-decking. `broken` caches duds (a missing generator is a stable
        # property of a topic) so we never re-attempt them.
        problem = None
        for topic in [planned] + [t for t in rotation if t.id != planned.id]:
            if topic.id in broken:
                continue
            made = _make_problem_for_topic(topic)
            if made is None:
                broken.add(topic.id)
                continue
            problem = made
            break
        if problem is None:
            break  # every topic's generator is broken; return what we have
        problems.append(problem)
    return problems


def _grade_topic(user, topic_id, outcome, today):
    """Apply an answer outcome to a topic's SM-2 schedule (once-per-day rule).

    `outcome` is one of the keys in `_OUTCOME_QUALITY`; anything else is ignored
    (defensive against a malformed client report). Implements the grading rule:
    the first answer for a topic each day sets the schedule, later repeats may
    only pull it down.

    The rule is applied by recomputing from a fixed base. On the first grade of
    the day we snapshot the topic's SM-2 state and remember the quality applied.
    On a repeat we take min(previously-applied quality, this quality): if it's
    not lower, nothing changes (a passing repeat can't raise the schedule); if it
    is lower, we recompute the TopicReview from the *snapshot* with the worse
    quality. Recomputing from the snapshot (rather than the current state) means
    repeated misses don't compound — the day's net effect is always one SM-2
    update from a single base.
    """
    quality = _OUTCOME_QUALITY.get(outcome)
    if quality is None:
        return

    review, _ = TopicReview.objects.get_or_create(user=user, topic_id=topic_id)
    grade = DailyTopicGrade.objects.filter(
        user=user, topic_id=topic_id, date=today
    ).first()

    if grade is None:
        # First occurrence today: snapshot the pre-grade state, then apply.
        base = (review.ease, review.interval, review.repetitions)
        DailyTopicGrade.objects.create(
            user=user, topic_id=topic_id, date=today,
            applied_quality=quality,
            snapshot_ease=base[0], snapshot_interval=base[1], snapshot_repetitions=base[2],
        )
    else:
        # Repeat today: only a strictly worse grade changes anything.
        if quality >= grade.applied_quality:
            return
        base = (grade.snapshot_ease, grade.snapshot_interval, grade.snapshot_repetitions)
        grade.applied_quality = quality
        grade.save(update_fields=["applied_quality"])

    ease, interval, repetitions = srs.update(base[0], base[1], base[2], quality)
    review.ease = ease
    review.interval = interval
    review.repetitions = repetitions
    review.due_date = today + datetime.timedelta(days=interval)
    review.save(update_fields=["ease", "interval", "repetitions", "due_date"])
    logger.info(
        "Graded topic %s for user %s: q=%d -> interval=%d, due %s",
        topic_id, user.id, quality, interval, review.due_date,
    )


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
        problems = _generate_problems(user, settings.questions_per_day, today)
        logger.info(
            "Built new deck for user %s with %d/%d problems",
            user.id, len(problems), settings.questions_per_day,
        )
        return DailyDeck.objects.create(
            user=user, date=today, problems=problems, current_index=0
        )
    missing = settings.questions_per_day - len(deck.problems)
    if missing > 0:
        existing = _deck_topic_ids(deck)
        extra = _generate_problems(user, missing, today, existing=existing)
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
    existing = _deck_topic_ids(deck)
    extra = _generate_problems(user, missing, today, existing=existing)
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
    new_tail = _generate_problems(user, remaining, today)
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
        "topic_name": _topic_name(current.get("topic_id")),
        "current_number": deck.current_index + 1,
        "total": total,
    }


def _topic_name(topic_id):
    """Resolve a stored problem's topic id to its display name, or None.

    Problems store only `topic_id` (not the name), so the card's topic label is
    looked up here at display time — which also keeps it current if a topic is
    renamed. Returns None when the id is missing (problems stored before topic
    attribution) or the topic no longer exists, so the client simply omits the
    label rather than showing a stale or broken one.
    """
    if topic_id is None:
        return None
    return Topic.objects.filter(id=topic_id).values_list("topic_name", flat=True).first()


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

    The optional JSON body `{"outcome": "correct_first"|"correct_second"|
    "incorrect"}` reports how the card being left was answered; it updates that
    card's topic's SM-2 schedule (see `_grade_topic`). It's optional so a stray
    advance with no answer (the midnight-rollover case) simply doesn't grade.
    """
    auth = _require_auth(request)
    if auth:
        return auth
    today = _client_today(request)
    existing = DailyDeck.objects.filter(user=request.user, date=today).first()
    deck = _get_or_create_today_deck(request.user, today)
    if existing is not None and deck.current_index < len(deck.problems):
        # Grade the card being left before stepping past it. Only a real,
        # existing deck advance grades — a stray advance that just built today's
        # deck (current_index 0, nothing answered) must not.
        outcome = _advance_outcome(request)
        card = deck.problems[deck.current_index]
        topic_id = card.get("topic_id")
        if outcome and topic_id is not None:
            _grade_topic(request.user, topic_id, outcome, today)
        deck.current_index += 1
        deck.save(update_fields=["current_index"])
        logger.debug(
            "User %s advanced deck to %d/%d",
            request.user.id, deck.current_index, len(deck.problems),
        )
    return JsonResponse(_deck_payload(request.user, deck))


def _advance_outcome(request):
    """The reported answer outcome from an advance request body, or None.

    Tolerant by design: a missing/empty/malformed body (or missing key) yields
    None so the advance still proceeds ungraded. Validation of the value itself
    happens in `_grade_topic`.
    """
    if not request.body:
        return None
    try:
        return json.loads(request.body).get("outcome")
    except (ValueError, AttributeError):
        logger.warning("Ignoring malformed advance body for user %s", request.user.id)
        return None
