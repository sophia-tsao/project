"""Math-correctness tests for the ``lib_geometry_gen`` library overrides.

For each overridden generator we run it many times under a fixed seed, parse
the inputs back out of the PROBLEM string with a regex, independently recompute
the expected answer, and assert the generator's stated solution matches. We
also assert every solution is typeable: no banned LaTeX/notation tokens and no
decimal carrying more than three fractional digits.
"""
import math
import random
import re
from fractions import Fraction

from django.test import TestCase

# Importing the module runs its @register side effects.
from myapp.generators import lib_geometry_gen  # noqa: F401
from myapp.generators import LOCAL_GENERATORS

SAMPLES = 500

# Tokens that must never appear in a typeable solution.
_BANNED = ["\\frac", "\\sqrt", "\\langle", "\\rangle", "\\geq", "\\leq",
           "\\neq", "\\times", "\\cdot", "\\infty", "\\begin", "[", "]",
           "{", "}"]

# A decimal with 4+ fractional digits (evidence of unrounded output).
_LONG_DECIMAL = re.compile(r"\d+\.\d{4,}")


def _assert_typeable(test, solution):
    for tok in _BANNED:
        test.assertNotIn(tok, solution, f"banned token {tok!r} in {solution!r}")
    test.assertIsNone(
        _LONG_DECIMAL.search(solution),
        f"solution has >3 decimal places: {solution!r}",
    )
    # No trailing '.0' style integers rendered as floats.
    for number in re.findall(r"-?\d+\.\d+", solution):
        test.assertNotEqual(number[-2:], ".0", f"trailing .0 in {solution!r}")


def _num(value, places=3):
    """Mirror of _format.num for independent expected-value comparison."""
    rounded = round(float(value), places)
    if rounded == int(rounded):
        return str(int(rounded))
    text = f"{rounded:.{places}f}".rstrip("0").rstrip(".")
    return text if text else "0"


class AreaOfCircleTests(TestCase):
    PROBLEM = re.compile(r"radius \$(?P<r>\d+)\$")

    def test_area_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["area_of_circle"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            r = int(m.group("r"))
            self.assertEqual(solution, _num(math.pi * r * r), problem)
            _assert_typeable(self, solution)


class AreaGivenCenterPointTests(TestCase):
    PROBLEM = re.compile(
        r"center \$\((?P<cx>-?\d+), (?P<cy>-?\d+)\)\$ that passes through "
        r"the point \$\((?P<px>-?\d+), (?P<py>-?\d+)\)\$"
    )

    def test_area_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["area_of_circle_given_center_and_point"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            cx, cy = int(m.group("cx")), int(m.group("cy"))
            px, py = int(m.group("px")), int(m.group("py"))
            r2 = (px - cx) ** 2 + (py - cy) ** 2
            self.assertNotEqual(r2, 0, f"zero radius: {problem!r}")
            self.assertEqual(solution, _num(math.pi * r2), problem)
            _assert_typeable(self, solution)


class CircumferenceTests(TestCase):
    PROBLEM = re.compile(r"radius \$(?P<r>\d+)\$")

    def test_circumference_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["circumference"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            r = int(m.group("r"))
            self.assertEqual(solution, _num(2 * math.pi * r), problem)
            _assert_typeable(self, solution)


class SectorAreaTests(TestCase):
    PROBLEM = re.compile(
        r"radius \$(?P<r>\d+)\$ and central angle \$(?P<theta>\d+)\$ degrees"
    )

    def test_sector_area_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["sector_area"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            r = int(m.group("r"))
            theta = int(m.group("theta"))
            expected = (theta / 360) * math.pi * r * r
            self.assertEqual(solution, _num(expected), problem)
            _assert_typeable(self, solution)


class DistanceTwoPointsTests(TestCase):
    PROBLEM = re.compile(
        r"points \$\((?P<x1>-?\d+), (?P<y1>-?\d+)\)\$ and "
        r"\$\((?P<x2>-?\d+), (?P<y2>-?\d+)\)\$"
    )

    def test_distance_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["distance_two_points"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            x1, y1 = int(m.group("x1")), int(m.group("y1"))
            x2, y2 = int(m.group("x2")), int(m.group("y2"))
            expected = math.hypot(x2 - x1, y2 - y1)
            self.assertEqual(solution, _num(expected), problem)
            _assert_typeable(self, solution)


class MidpointTests(TestCase):
    PROBLEM = re.compile(
        r"points \$\((?P<x1>-?\d+), (?P<y1>-?\d+)\)\$ and "
        r"\$\((?P<x2>-?\d+), (?P<y2>-?\d+)\)\$"
    )
    SOLUTION = re.compile(
        r"^\((?P<mx>-?\d+(?:\.\d+)?), (?P<my>-?\d+(?:\.\d+)?)\)$"
    )

    def test_midpoint_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["midpoint_of_two_points"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            x1, y1 = int(m.group("x1")), int(m.group("y1"))
            x2, y2 = int(m.group("x2")), int(m.group("y2"))
            sm = self.SOLUTION.match(solution)
            self.assertIsNotNone(sm, f"bad pair format: {solution!r}")
            self.assertEqual(sm.group("mx"), _num((x1 + x2) / 2), problem)
            self.assertEqual(sm.group("my"), _num((y1 + y2) / 2), problem)
            _assert_typeable(self, solution)


class EuclidianNormTests(TestCase):
    PROBLEM = re.compile(r"vector \$\((?P<vec>[-\d, ]+)\)\$")

    def test_norm_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["euclidian_norm"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            components = [int(v) for v in m.group("vec").split(", ")]
            self.assertGreaterEqual(len(components), 2)
            self.assertLessEqual(len(components), 4)
            self.assertTrue(any(components), f"zero vector: {problem!r}")
            expected = math.sqrt(sum(c * c for c in components))
            self.assertEqual(solution, _num(expected), problem)
            _assert_typeable(self, solution)


def _parse_frac(text):
    text = text.strip()
    if "/" in text:
        n, d = text.split("/")
        return Fraction(int(n), int(d))
    return Fraction(int(text))


class EquationOfLineTests(TestCase):
    PROBLEM = re.compile(
        r"points \$\((?P<x1>-?\d+), (?P<y1>-?\d+)\)\$ and "
        r"\$\((?P<x2>-?\d+), (?P<y2>-?\d+)\)\$"
    )
    # y = <slope>x [+|- <intercept>]; slope may be '', '-', int, or a/b.
    SOLUTION = re.compile(
        r"^y = (?P<slope>-?\d+/\d+|-?\d+|-?)x"
        r"(?: (?P<sign>[+-]) (?P<b>\d+/\d+|\d+))?$"
    )

    def test_line_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["equation_of_line_from_two_points"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            x1, y1 = int(m.group("x1")), int(m.group("y1"))
            x2, y2 = int(m.group("x2")), int(m.group("y2"))
            self.assertNotEqual(x2, x1, f"vertical line: {problem!r}")
            self.assertNotEqual(y2, y1, f"horizontal line: {problem!r}")

            sm = self.SOLUTION.match(solution)
            self.assertIsNotNone(sm, f"bad line format: {solution!r}")
            slope_raw = sm.group("slope")
            if slope_raw in ("", "+"):
                got_m = Fraction(1)
            elif slope_raw == "-":
                got_m = Fraction(-1)
            else:
                got_m = _parse_frac(slope_raw)
            if sm.group("b") is None:
                got_b = Fraction(0)
            else:
                mag = _parse_frac(sm.group("b"))
                got_b = mag if sm.group("sign") == "+" else -mag

            expected_m = Fraction(y2 - y1, x2 - x1)
            expected_b = Fraction(y1) - expected_m * x1
            self.assertEqual(got_m, expected_m, f"slope wrong: {problem!r} -> {solution!r}")
            self.assertEqual(got_b, expected_b, f"intercept wrong: {problem!r} -> {solution!r}")
            _assert_typeable(self, solution)
