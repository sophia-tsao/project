"""Math-correctness tests for the ``lib_fractions_gen`` local overrides.

Each test parses the numbers out of the generated problem statement,
recomputes the expected answer independently, and asserts the generator's
solution matches exactly — including ascending order and reduced form. All
tests also guard that no untypeable notation (``[`` ``]`` ``{`` ``}`` or
``\\frac``) leaks into a solution.
"""
import random
import re
from fractions import Fraction
from math import gcd

from django.test import TestCase

# Importing the module runs its @register side effects.
from myapp.generators import lib_fractions_gen  # noqa: F401
from myapp.generators import LOCAL_GENERATORS

SAMPLES = 500

_BANNED = ("[", "]", "{", "}", "\\frac")


def _factors_of(n):
    divisors = set()
    i = 1
    while i * i <= n:
        if n % i == 0:
            divisors.add(i)
            divisors.add(n // i)
        i += 1
    return sorted(divisors)


def _assert_typeable(test, solution):
    for token in _BANNED:
        test.assertNotIn(token, solution, f"untypeable token in: {solution!r}")


class CommonFactorsTests(TestCase):
    PAT = re.compile(r"common factors of (?P<a>\d+) and (?P<b>\d+)")

    def test_solution_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["common_factors"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            _assert_typeable(self, solution)
            m = self.PAT.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a, b = int(m.group("a")), int(m.group("b"))
            expected = sorted(set(_factors_of(a)) & set(_factors_of(b)))
            self.assertEqual(solution, ", ".join(str(v) for v in expected))


class FactorsTests(TestCase):
    PAT = re.compile(r"factors of (?P<n>\d+)")

    def test_solution_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["factors"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            _assert_typeable(self, solution)
            m = self.PAT.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            n = int(m.group("n"))
            expected = _factors_of(n)
            self.assertEqual(solution, ", ".join(str(v) for v in expected))
            got = [int(v) for v in solution.split(", ")]
            self.assertEqual(got, sorted(got), f"not ascending: {solution!r}")


class FractionMultiplicationTests(TestCase):
    PAT = re.compile(r"\\frac\{(\d+)\}\{(\d+)\} \\cdot \\frac\{(\d+)\}\{(\d+)\}")

    def test_solution_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["fraction_multiplication"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            _assert_typeable(self, solution)
            m = self.PAT.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a, b, c, d = (int(g) for g in m.groups())
            expected = Fraction(a * c, b * d)
            want = (
                str(expected.numerator)
                if expected.denominator == 1
                else f"{expected.numerator}/{expected.denominator}"
            )
            self.assertEqual(solution, want)


class DivideFractionsTests(TestCase):
    PAT = re.compile(r"\\frac\{(\d+)\}\{(\d+)\} \\div \\frac\{(\d+)\}\{(\d+)\}")

    def test_solution_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["divide_fractions"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            _assert_typeable(self, solution)
            m = self.PAT.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a, b, c, d = (int(g) for g in m.groups())
            expected = Fraction(a * d, b * c)
            want = (
                str(expected.numerator)
                if expected.denominator == 1
                else f"{expected.numerator}/{expected.denominator}"
            )
            self.assertEqual(solution, want)


class GreatestCommonDivisorTests(TestCase):
    PAT = re.compile(r"GCD\) of (?P<nums>[\d, ]+?)\. ")

    def test_solution_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["greatest_common_divisor"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            _assert_typeable(self, solution)
            m = self.PAT.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            nums = [int(v) for v in m.group("nums").split(", ")]
            self.assertIn(len(nums), (2, 3))
            expected = 0
            for value in nums:
                expected = gcd(expected, value)
            self.assertEqual(solution, str(expected))


class DiceSumProbabilityTests(TestCase):
    PAT = re.compile(r"(?P<n>\d+) fair (?P<sides>\d+)-sided dice.*sum of (?P<t>\d+)")

    def test_solution_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["dice_sum_probability"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            _assert_typeable(self, solution)
            m = self.PAT.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            self.assertEqual(int(m.group("n")), 2)
            sides = int(m.group("sides"))
            target = int(m.group("t"))
            favorable = sum(
                1
                for x in range(1, sides + 1)
                for y in range(1, sides + 1)
                if x + y == target
            )
            expected = Fraction(favorable, sides * sides)
            want = (
                str(expected.numerator)
                if expected.denominator == 1
                else f"{expected.numerator}/{expected.denominator}"
            )
            self.assertEqual(solution, want)
