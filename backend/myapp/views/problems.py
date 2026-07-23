import logging
import random
import re

from django.http import JsonResponse

import mathgenerator

from ..models import Topic
from ..generators import LOCAL_GENERATORS
from ..generators._format import num as _num
from .common import _require_auth

logger = logging.getLogger(__name__)

# Matches an *over-precise* decimal (4+ fractional digits) anywhere in a string,
# e.g. the ``523.5987755982989`` inside ``"523.5987755982989 m^3"``. Decimals
# already at three or fewer places are left exactly as written, so a generator's
# intentional formatting (``5.0*10^4``, ``46.7``) is never disturbed — only the
# long floats some library generators emit get normalised. A leading sign is
# captured so negatives round correctly.
_LONG_DECIMAL_RE = re.compile(r"-?\d+\.\d{4,}")


def _round_decimals(text):
    """Round every over-precise decimal in `text` to the nearest thousandth.

    Operates per-number rather than requiring the whole string to be a single
    float, so answers carrying units or extra words (``"523.5987755982989
    m^3"``) are rounded too — the previous logic ran ``float()`` on the whole
    string and left any unit-suffixed answer at full precision. Only decimals
    with four or more fractional digits are touched (see `_LONG_DECIMAL_RE`);
    each is reformatted via the shared `num` helper (round to 3 places, drop a
    trailing ``.0``). Integers and already-short decimals pass through unchanged.
    """
    return _LONG_DECIMAL_RE.sub(lambda m: _num(m.group()), text)


def _make_problem_for_topic(topic):
    """Generate a single problem for one specific topic.

    Returns a dict with 'problem', 'solution', and 'topic_id', or None if the
    topic has no usable generator. The `topic_id` ties the stored problem back
    to the topic it came from, so an answer can be attributed to that topic for
    spaced-repetition scheduling (see myapp.srs); it isn't sent to the client.
    """
    name = topic.generator_name
    if not name:
        return None
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

    # Round every decimal in the solution to the nearest thousandth. This runs
    # per-number, so it also handles answers that carry units or extra text
    # (e.g. "523.5987755982989 m^3"), which a whole-string float() cannot. If
    # rounding actually changed the answer, tell the student to round too, so
    # their typed answer can match the (now-rounded) solution.
    rounded_sol = _round_decimals(sol_str)
    if rounded_sol != sol_str:
        problem = problem.rstrip() + " Round to the nearest thousandth if necessary."
    sol_str = rounded_sol

    # The problem text can also contain unrounded decimals (some library
    # generators embed computed values in the prompt). Round those too so a
    # student never sees a 16-digit decimal anywhere on the card. LaTeX in the
    # problem uses no bare decimal tokens that this would corrupt.
    problem = _round_decimals(problem)

    return {"problem": problem, "solution": sol_str, "topic_id": topic.id}


def _make_problem(user):
    """Generate a single problem from a random one of the user's selected topics.

    Returns a dict with 'problem', 'solution', and 'topic_id', or None if no
    topics are selected. Topic *selection* lives here; the actual generation for
    a chosen topic is delegated to `_make_problem_for_topic`. The deck layer will
    replace this random choice with due-ordered selection, but generate_problem
    and existing callers keep this uniform-random behavior.
    """
    topics = list(
        Topic.objects.filter(selections__user=user).exclude(generator_name__isnull=True)
    )
    if not topics:
        return None
    return _make_problem_for_topic(random.choice(topics))


def generate_problem(request):
    auth = _require_auth(request)
    if auth:
        return auth
    result = _make_problem(request.user)
    if result is None:
        return JsonResponse({"no_topics": True})
    return JsonResponse(result)
