"""Math-correctness tests for the G4 percentage/finance overrides.

For each generator we parse the numeric inputs back out of the problem text,
recompute the expected answer with the same 3dp rounding, and assert it matches
the generator's solution over many random samples. We also guard typeability:
no banned LaTeX tokens, no stray ``%`` sign in the solution, and no number
carrying more than three decimals.
"""
import math
import random
import re

from django.test import TestCase

# Importing the module runs its @register side effects.
from myapp.generators import lib_finance_gen  # noqa: F401
from myapp.generators import LOCAL_GENERATORS
from myapp.generators._format import num

SAMPLES = 500

# Tokens that must never appear in a typeable solution.
_BANNED = [
    r"\frac", r"\sqrt", r"\geq", r"\leq", r"\neq", r"\times", r"\cdot",
    r"\infty", r"\begin", "{", "}", "[", "]",
]

# A number token with 4+ decimal places (would break the 3dp typeable rule).
_TOO_MANY_DECIMALS = re.compile(r"\d+\.\d{4,}")


def _assert_typeable(test, problem, solution):
    for token in _BANNED:
        test.assertNotIn(token, solution, f"banned {token!r} in solution: {solution!r}")
    # No percent sign in the answer -- percentages are returned as bare numbers.
    test.assertNotIn("%", solution, f"stray % in solution: {solution!r}")
    test.assertNotRegex(solution, _TOO_MANY_DECIMALS,
                        f">3 decimals in solution: {solution!r}")
    # Solutions must never carry a trailing '.0'.
    for part in re.split(r"[,\s]+", solution):
        test.assertFalse(re.fullmatch(r"-?\d+\.0", part),
                         f"trailing .0 in solution: {solution!r}")


class PercentageTests(TestCase):
    def test_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["percentage"]
        pat = re.compile(r"What is \$(\d+)\\%\$ of \$(\d+)\$")
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = pat.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            p, n = int(m.group(1)), int(m.group(2))
            self.assertEqual(solution, num(p / 100 * n), f"for {p}%,{n}: {problem!r}")
            _assert_typeable(self, problem, solution)


class PercentageDifferenceTests(TestCase):
    def test_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["percentage_difference"]
        pat = re.compile(r"between \$(\d+)\$ and \$(\d+)\$")
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = pat.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a, b = int(m.group(1)), int(m.group(2))
            expected = num(abs(a - b) / ((a + b) / 2) * 100)
            self.assertEqual(solution, expected, f"for {a},{b}: {problem!r}")
            _assert_typeable(self, problem, solution)


class PercentageErrorTests(TestCase):
    def test_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["percentage_error"]
        pat = re.compile(r"observed value is \$(\d+)\$ and the exact value is \$(\d+)\$")
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = pat.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            observed, exact = int(m.group(1)), int(m.group(2))
            expected = num(abs(observed - exact) / abs(exact) * 100)
            self.assertEqual(solution, expected, f"for {observed},{exact}: {problem!r}")
            _assert_typeable(self, problem, solution)


class SimpleInterestTests(TestCase):
    def test_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["simple_interest"]
        pat = re.compile(
            r"principal of \$(\d+)\$ dollars at a rate of \$(\d+)\\%\$ per year "
            r"for \$(\d+)\$ years")
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = pat.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            p, r, t = int(m.group(1)), int(m.group(2)), int(m.group(3))
            self.assertEqual(solution, num(p * r * t / 100), f"for {p},{r},{t}: {problem!r}")
            _assert_typeable(self, problem, solution)


class CompoundInterestTests(TestCase):
    def test_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["compound_interest"]
        pat = re.compile(
            r"principal of \$(\d+)\$ dollars is invested at a rate of "
            r"\$(\d+)\\%\$ per year, compounded annually, for \$(\d+)\$ years")
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = pat.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            p, r, t = int(m.group(1)), int(m.group(2)), int(m.group(3))
            expected = num(p * (1 + r / 100) ** t)
            self.assertEqual(solution, expected, f"for {p},{r},{t}: {problem!r}")
            _assert_typeable(self, problem, solution)


class ProfitLossPercentTests(TestCase):
    def test_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["profit_loss_percent"]
        pat = re.compile(r"cost price of \$(\d+)\$ and a sell price of \$(\d+)\$")
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = pat.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            cost, sell = int(m.group(1)), int(m.group(2))
            expected = num(abs(sell - cost) / cost * 100)
            self.assertEqual(solution, expected, f"for {cost},{sell}: {problem!r}")
            # Direction word must agree with the numbers.
            kind = "profit" if sell >= cost else "loss"
            self.assertIn(kind, problem, f"wrong direction for {cost},{sell}")
            _assert_typeable(self, problem, solution)


class ConditionalProbabilityTests(TestCase):
    def test_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["conditional_probability"]
        pat = re.compile(r"\$(\d+)\$ people said they exercise, and of those, \$(\d+)\$")
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = pat.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            b_count, ab_count = int(m.group(1)), int(m.group(2))
            expected = num(ab_count / b_count)
            self.assertEqual(solution, expected, f"for {ab_count}/{b_count}: {problem!r}")
            # A probability is always in [0, 1].
            self.assertLessEqual(float(solution), 1.0)
            self.assertGreaterEqual(float(solution), 0.0)
            _assert_typeable(self, problem, solution)


class BinomialDistributionTests(TestCase):
    def test_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["binomial_distribution"]
        pat = re.compile(
            r"each of \$(\d+)\$ independent trials the probability of success "
            r"is \$([\d.]+)\$\. What is the probability of exactly \$(\d+)\$")
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = pat.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            n, p, k = int(m.group(1)), float(m.group(2)), int(m.group(3))
            expected = num(math.comb(n, k) * p ** k * (1 - p) ** (n - k))
            self.assertEqual(solution, expected, f"for n={n},p={p},k={k}: {problem!r}")
            self.assertLessEqual(float(solution), 1.0)
            self.assertGreaterEqual(float(solution), 0.0)
            _assert_typeable(self, problem, solution)
