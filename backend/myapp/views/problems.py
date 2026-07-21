import logging
import random

from django.http import JsonResponse

import mathgenerator

from ..models import Topic
from ..generators import LOCAL_GENERATORS
from .common import _require_auth

logger = logging.getLogger(__name__)


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
