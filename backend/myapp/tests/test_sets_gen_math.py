"""Math-correctness test for the ``set_operation`` generator.

Parses the two sets and the requested operation out of the problem statement,
recomputes the expected result independently, and asserts the generator's
solution matches — over many random samples. Also guards the two invariants the
generator promises: the answer is a sorted, space-free comma list, and it is
never empty (an empty answer would be impossible to type).
"""
import random
import re

from django.test import TestCase

# Importing the module runs its @register side effect.
from myapp.generators import sets_gen  # noqa: F401
from myapp.generators import LOCAL_GENERATORS

SAMPLES = 2000

# Map the human operation name in the problem to a set computation.
_OPS = {
    "union": lambda a, b: a | b,
    "intersection": lambda a, b: a & b,
    "difference A - B": lambda a, b: a - b,
    "difference B - A": lambda a, b: b - a,
    "symmetric difference": lambda a, b: a ^ b,
}

PROBLEM = re.compile(
    r"Given A = \{(?P<a>[\d, ]+)\} and B = \{(?P<b>[\d, ]+)\}, "
    r"find the (?P<op>union|intersection|difference A - B|difference B - A|"
    r"symmetric difference) "
)


def _parse_set(text):
    return {int(v) for v in text.split(", ")}


class SetOperationTests(TestCase):
    def test_solution_matches_operation(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["set_operation"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")

            a = _parse_set(m.group("a"))
            b = _parse_set(m.group("b"))
            expected = _OPS[m.group("op")](a, b)

            # Non-empty and typeable: sorted ints, comma-separated, no spaces.
            self.assertNotEqual(solution, "", f"empty answer for: {problem!r}")
            self.assertRegex(solution, r"^\d+(?:,\d+)*$", f"bad format: {solution!r}")

            got = [int(v) for v in solution.split(",")]
            self.assertEqual(got, sorted(got), f"answer not sorted: {solution!r}")
            self.assertEqual(set(got), expected, f"wrong set for: {problem!r}")
