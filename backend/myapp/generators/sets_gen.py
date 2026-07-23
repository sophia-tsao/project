"""Solveki-local set-operation generator.

This module contains a single generator, :func:`set_operation`, whose name is
chosen deliberately to *override* the stock ``mathgenerator`` generator of the
same name (``_make_problem_for_topic`` resolves ``LOCAL_GENERATORS`` before the
library). The library version is unusable here for two reasons: its problem
string is missing a closing ``$`` (so the descriptive text renders as italic
math), and its answer is five Python ``set`` literals — untypeable in the
answer box, which does an exact/``parseFloat`` match.

Our version asks for a single operation and returns a typeable, sorted,
comma-separated list of integers. It is named without the usual category prefix
precisely so the ``generator_name`` already stored on the Topic keeps working.
"""
import random

from ._registry import register

# (display symbol, human name, how to compute the result set from a, b).
_OPERATIONS = [
    ("A ∪ B", "union", lambda a, b: a | b),
    ("A ∩ B", "intersection", lambda a, b: a & b),
    ("A - B", "difference A - B", lambda a, b: a - b),
    ("B - A", "difference B - A", lambda a, b: b - a),
    ("A △ B", "symmetric difference", lambda a, b: a ^ b),
]


def _set_str(values):
    """Render a set of ints as ``{1, 3, 4}`` for the problem statement."""
    return "{" + ", ".join(str(v) for v in sorted(values)) + "}"


def _answer_str(values):
    """Render the result as a typeable, sorted, comma-separated list."""
    return ",".join(str(v) for v in sorted(values))


@register
def set_operation(pool_min=1, pool_max=12):
    r"""Union, Intersection, Difference of Two Sets

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Given A = {1, 3, 4} and B = {3, 5, 8}, find the union (A ∪ B)... | 1,3,4,5,8 |

    Overrides the stock ``mathgenerator`` ``set_operation``. Asks for a single
    operation so the answer is one typeable list. ``A`` and ``B`` are built to
    share at least one element and each hold at least one unique element, so
    every operation (including intersection and both differences) yields a
    non-empty result — an empty answer would be impossible to type.
    """
    pool = list(range(pool_min, pool_max + 1))
    random.shuffle(pool)
    # Partition disjoint chunks off the shuffled pool: elements common to both
    # sets, elements only in A, and elements only in B. Each is non-empty.
    n_shared = random.randint(1, 3)
    n_a_only = random.randint(1, 3)
    n_b_only = random.randint(1, 3)
    shared = pool[:n_shared]
    a_only = pool[n_shared:n_shared + n_a_only]
    b_only = pool[n_shared + n_a_only:n_shared + n_a_only + n_b_only]

    a = set(shared) | set(a_only)
    b = set(shared) | set(b_only)

    symbol, name, compute = random.choice(_OPERATIONS)
    result = compute(a, b)

    problem = (
        f"Given A = {_set_str(a)} and B = {_set_str(b)}, "
        f"find the {name} ({symbol}). "
        "List the elements in increasing order, separated by commas with no "
        "spaces (e.g. 1,3,5)."
    )
    solution = _answer_str(result)
    return problem, solution
