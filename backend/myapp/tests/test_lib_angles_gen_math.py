"""Math-correctness tests for the G3 angle/trig/conversion overrides.

For each generator we parse the numeric inputs back out of the problem text,
recompute the expected answer with the same 3dp rounding, and assert it matches
the generator's solution over many random samples. We also guard typeability:
no banned LaTeX tokens, and no number carrying more than three decimals.
"""
import math
import random
import re
from fractions import Fraction

from django.test import TestCase

# Importing the module runs its @register side effects.
from myapp.generators import lib_angles_gen  # noqa: F401
from myapp.generators import LOCAL_GENERATORS
from myapp.generators._format import num

SAMPLES = 500

# Tokens that must never appear in a typeable problem or solution.
_BANNED = [
    r"\frac", r"\sqrt", r"\geq", r"\leq", r"\neq", r"\times", r"\cdot",
    r"\infty", r"\begin", r"\theta", r"\sin", r"\cos", r"\sec", r"\div",
    "{", "}", "[", "]",
]

# A number token with 4+ decimal places (would break the 3dp typeable rule).
_TOO_MANY_DECIMALS = re.compile(r"\d+\.\d{4,}")


def _assert_typeable(test, problem, solution):
    for token in _BANNED:
        test.assertNotIn(token, solution, f"banned {token!r} in solution: {solution!r}")
    test.assertNotRegex(solution, _TOO_MANY_DECIMALS,
                        f">3 decimals in solution: {solution!r}")
    # Solutions must never carry a trailing '.0'.
    for part in re.split(r"[,\s]+", solution):
        test.assertFalse(re.fullmatch(r"-?\d+\.0", part),
                         f"trailing .0 in solution: {solution!r}")


class AngleRegularPolygonTests(TestCase):
    def test_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["angle_regular_polygon"]
        pat = re.compile(r"polygon with \$(\d+)\$ sides")
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = pat.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            n = int(m.group(1))
            expected = num((n - 2) * 180 / n)
            self.assertEqual(solution, expected, f"for n={n}: {problem!r}")
            _assert_typeable(self, problem, solution)


class AngleBtwVectorsTests(TestCase):
    def test_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["angle_btw_vectors"]
        pat = re.compile(r"vectors \(([-\d, ]+)\) and \(([-\d, ]+)\)")
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = pat.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a = [int(v) for v in m.group(1).split(", ")]
            b = [int(v) for v in m.group(2).split(", ")]
            dot = sum(x * y for x, y in zip(a, b))
            mag_a = math.sqrt(sum(x * x for x in a))
            mag_b = math.sqrt(sum(x * x for x in b))
            cos_theta = max(-1.0, min(1.0, dot / (mag_a * mag_b)))
            expected = num(math.acos(cos_theta))
            self.assertEqual(solution, expected, f"for {a},{b}: {problem!r}")
            _assert_typeable(self, problem, solution)


class DegreeToRadTests(TestCase):
    def test_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["degree_to_rad"]
        pat = re.compile(r"Convert \$(\d+)\$ degrees to radians")
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = pat.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            deg = int(m.group(1))
            expected = num(deg * math.pi / 180)
            self.assertEqual(solution, expected, f"for {deg}: {problem!r}")
            _assert_typeable(self, problem, solution)


class RadianToDegTests(TestCase):
    def test_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["radian_to_deg"]
        pat = re.compile(r"Convert \$([-\d.]+)\$ radians to degrees")
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = pat.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            rad = float(m.group(1))
            expected = num(rad * 180 / math.pi)
            self.assertEqual(solution, expected, f"for {rad}: {problem!r}")
            _assert_typeable(self, problem, solution)


class ComplexToPolarTests(TestCase):
    def test_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["complex_to_polar"]
        pat = re.compile(r"number \$(-?\d+)([+-]\d+)i\$")
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = pat.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a = int(m.group(1))
            b = int(m.group(2))
            expected = f"{num(math.sqrt(a * a + b * b))}, {num(math.atan2(b, a))}"
            self.assertEqual(solution, expected, f"for {a},{b}: {problem!r}")
            _assert_typeable(self, problem, solution)


class TrigDifferentiationTests(TestCase):
    def test_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["trig_differentiation"]
        expected_map = dict(lib_angles_gen._DERIVATIVES)
        pat = re.compile(r"Differentiate \$(.+?)\$ with respect")
        seen = set()
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = pat.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            func = m.group(1)
            self.assertIn(func, expected_map, f"unknown func: {func!r}")
            self.assertEqual(solution, expected_map[func], f"for {func}")
            seen.add(func)
            _assert_typeable(self, problem, solution)
        # Over 500 runs the full finite set should appear.
        self.assertEqual(seen, set(expected_map))


class FractionToDecimalTests(TestCase):
    def test_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["fraction_to_decimal"]
        pat = re.compile(r"fraction \$(\d+)/(\d+)\$")
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = pat.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            n, d = int(m.group(1)), int(m.group(2))
            expected = num(n / d)
            self.assertEqual(solution, expected, f"for {n}/{d}: {problem!r}")
            _assert_typeable(self, problem, solution)


class CelsiusToFahrenheitTests(TestCase):
    def test_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["celsius_to_fahrenheit"]
        pat = re.compile(r"Convert \$(-?\d+)\$ degrees Celsius")
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = pat.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            c = int(m.group(1))
            expected = num(Fraction(c) * 9 / 5 + 32)
            self.assertEqual(solution, expected, f"for {c}: {problem!r}")
            _assert_typeable(self, problem, solution)
