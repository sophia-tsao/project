import logging
import random

from django.http import JsonResponse

import mathgenerator

from ..models import Topic
from ..generators import LOCAL_GENERATORS
from .common import _require_auth

logger = logging.getLogger(__name__)


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
