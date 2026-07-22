"""SuperMemo-2 (SM-2) spaced-repetition scheduling.

This module is the whole SM-2 algorithm and nothing else: pure functions with no
database, request, or clock access, so the scheduling math can be reasoned about
and unit-tested in isolation. Callers (the deck layer) own persistence and dates;
this module only maps (current state, grade) -> (next state) and (state) -> (days
until next review).

State is the SM-2 triple:
  - ease        the ease factor, a multiplier on the interval (starts 2.5)
  - interval    days until the next review
  - repetitions consecutive successful reviews (resets to 0 on a lapse)

Grades follow SM-2's 0-5 quality scale, where q >= 3 is a successful recall and
q < 3 is a lapse. Solveki derives the quality from the answer outcome upstream;
this module just consumes it.
"""

# SM-2 constants.
MIN_EASE = 1.3   # ease floor: below this, intervals stop growing ("ease hell")
INITIAL_EASE = 2.5
PASSING_GRADE = 3  # quality >= this counts as a successful recall

# Maximum interval, in days. SM-2 itself has no cap; this borrows Anki's notion
# of a maximum interval, but not its value: Anki defaults to ~100 years, which
# for a math-practice app would let a mastered topic vanish for good. A 1-year
# cap keeps even well-known topics resurfacing at least annually so the skill is
# refreshed rather than forgotten. Tunable in one place.
MAX_INTERVAL = 365


def update_ease(ease, quality):
    """Return the new ease factor after a review graded `quality` (0-5).

    This is SM-2's ease update, applied on *every* review (pass or lapse) and
    then clamped to the 1.3 floor. Higher quality nudges ease up; lower quality
    pulls it down, so hard-but-correct answers make future intervals grow more
    slowly.
    """
    ease = ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    return max(ease, MIN_EASE)


def update(ease, interval, repetitions, quality):
    """Advance SM-2 state by one review.

    Returns a new `(ease, interval, repetitions)` triple; does not mutate inputs.

    On a successful recall (`quality >= 3`) the interval grows: the first success
    schedules 1 day out, the second 6 days, and thereafter the previous interval
    times the ease factor (rounded), capped at `MAX_INTERVAL` so a mastered topic
    still resurfaces. On a lapse (`quality < 3`) the item is reset to be
    relearned — repetitions to 0 and interval to 1 day (due tomorrow) — so a topic
    answered wrong resurfaces quickly. The ease factor is updated in both cases.
    """
    new_ease = update_ease(ease, quality)
    if quality >= PASSING_GRADE:
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = round(interval * new_ease)
        new_interval = min(new_interval, MAX_INTERVAL)
        new_repetitions = repetitions + 1
    else:
        new_interval = 1
        new_repetitions = 0
    return new_ease, new_interval, new_repetitions
