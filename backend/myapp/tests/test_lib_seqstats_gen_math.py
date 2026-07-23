"""Math-correctness tests for the G5 sequence / integral / statistics overrides.

For each generator we parse the numeric inputs back out of the problem text,
recompute the expected answer with the same rounding the generator states, and
assert it matches over many random samples. We also guard typeability: no
banned LaTeX tokens, no braces/brackets, no number carrying more than three
decimals, and none of the library's original "arithmatic"/"mdian" typos.
"""
import math
import re
from fractions import Fraction

from django.test import TestCase

# Importing the module runs its @register side effects.
from myapp.generators import lib_seqstats_gen  # noqa: F401
from myapp.generators import LOCAL_GENERATORS
from myapp.generators._format import num, frac_from

SAMPLES = 400

# Tokens that must never appear in a typeable problem or solution.
_BANNED = [
    r"\frac", r"\sqrt", r"\geq", r"\leq", r"\neq", r"\times", r"\cdot",
    r"\infty", r"\begin", "{", "}", "[", "]",
]

# A number token with 4+ decimal places (would break the 3dp typeable rule).
_TOO_MANY_DECIMALS = re.compile(r"\d+\.\d{4,}")

NUM = r"-?\d+(?:\.\d+)?"
INT = r"-?\d+"
# An integer or reduced fraction a/b.
FRAC = r"-?\d+(?:/\d+)?"


def _median(values):
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _parse_frac(text):
    if "/" in text:
        p, q = text.split("/")
        return Fraction(int(p), int(q))
    return Fraction(int(text))


class TypeabilityMixin:
    """Shared guards run against every generated (problem, solution)."""

    def _assert_typeable(self, problem, solution):
        for text in (problem, solution):
            for token in _BANNED:
                self.assertNotIn(
                    token, text, f"banned token {token!r} in {text!r}"
                )
            self.assertIsNone(
                _TOO_MANY_DECIMALS.search(text),
                f">3 decimals in {text!r}",
            )
            self.assertNotIn("arithmatic", text)
            self.assertNotIn("mdian", text)


class MeanMedianTests(TypeabilityMixin, TestCase):
    DATA = re.compile(r"series of numbers: (?P<data>[\d, ]+?)\.")
    SOLUTION = re.compile(rf"(?P<mean>{NUM}), (?P<median>{NUM})")

    def test_mean_median(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["mean_median"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            self._assert_typeable(problem, solution)
            m = self.DATA.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            data = [int(v) for v in m.group("data").split(", ")]
            exp_mean = round(sum(data) / len(data), 3)
            exp_median = round(_median(data), 3)
            s = self.SOLUTION.search(solution)
            self.assertIsNotNone(s, f"could not parse solution: {solution!r}")
            self.assertAlmostEqual(float(s.group("mean")), exp_mean, places=3)
            self.assertAlmostEqual(
                float(s.group("median")), exp_median, places=3
            )


class DataSummaryTests(TypeabilityMixin, TestCase):
    DATA = re.compile(r"data set: (?P<data>[\d, ]+?)\.")
    SOLUTION = re.compile(rf"(?P<mean>{NUM}), (?P<sd>{NUM}), (?P<var>{NUM})")

    def test_data_summary(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["data_summary"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            self._assert_typeable(problem, solution)
            m = self.DATA.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            data = [int(v) for v in m.group("data").split(", ")]
            n = len(data)
            mean = sum(data) / n
            variance = sum((x - mean) ** 2 for x in data) / n
            sd = math.sqrt(variance)
            s = self.SOLUTION.search(solution)
            self.assertIsNotNone(s, f"could not parse solution: {solution!r}")
            self.assertAlmostEqual(
                float(s.group("mean")), round(mean, 3), places=3
            )
            self.assertAlmostEqual(
                float(s.group("sd")), round(sd, 3), places=3
            )
            self.assertAlmostEqual(
                float(s.group("var")), round(variance, 3), places=3
            )


class ArithmeticProgressionSumTests(TypeabilityMixin, TestCase):
    PROBLEM = re.compile(
        rf"first (?P<n>\d+) terms .* first term (?P<a>{INT}) and common "
        rf"difference (?P<d>{INT})"
    )

    def test_ap_sum(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["arithmetic_progression_sum"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            self._assert_typeable(problem, solution)
            self.assertNotIn(".", solution)  # always an integer, no .0
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            n, a, d = int(m.group("n")), int(m.group("a")), int(m.group("d"))
            expected = n * (2 * a + (n - 1) * d) // 2
            self.assertEqual(int(solution), expected)


class GeometricProgressionTests(TypeabilityMixin, TestCase):
    PROBLEM = re.compile(
        rf"first term a = (?P<a>{INT}) and common ratio r = (?P<r>{INT})\. "
        rf"Find the (?P<n>\d+)th term"
    )

    def test_gp_term(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["geometric_progression"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            self._assert_typeable(problem, solution)
            self.assertNotIn(".", solution)
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a, r, n = int(m.group("a")), int(m.group("r")), int(m.group("n"))
            self.assertEqual(int(solution), a * r ** (n - 1))


class DefiniteIntegralTests(TypeabilityMixin, TestCase):
    PROBLEM = re.compile(
        rf"integral of (?P<p>{INT})x\^2 \+ (?P<q>{INT})x \+ (?P<s>{INT}) "
        rf"from x = (?P<a>{INT}) to x = (?P<b>{INT})"
    )

    def test_definite_integral(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["definite_integral"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            self._assert_typeable(problem, solution)
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            p, q, s = int(m.group("p")), int(m.group("q")), int(m.group("s"))
            a, b = int(m.group("a")), int(m.group("b"))

            def antideriv(x):
                x = Fraction(x)
                return Fraction(p, 3) * x ** 3 + Fraction(q, 2) * x ** 2 + s * x

            expected = antideriv(b) - antideriv(a)
            self.assertEqual(_parse_frac(solution), expected)


class PowerRuleIntegrationTests(TypeabilityMixin, TestCase):
    # Match integrand terms like "9x^5" or "3x".
    TERM = re.compile(r"(?P<coef>\d+)x(?:\^(?P<exp>\d+))?")

    def test_power_rule(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["power_rule_integration"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            self._assert_typeable(problem, solution)
            self.assertTrue(solution.endswith(" + C"), solution)

            # Parse the integrand from between "of " and the first ".".
            integrand_str = problem.split("of ", 1)[1].split(".", 1)[0]
            integrand = {}
            for tm in self.TERM.finditer(integrand_str):
                exp = int(tm.group("exp")) if tm.group("exp") else 1
                integrand[exp] = int(tm.group("coef"))
            self.assertTrue(integrand, f"no terms parsed: {problem!r}")

            # Expected antiderivative, canonical descending.
            antideriv = {e + 1: Fraction(c, e + 1) for e, c in integrand.items()}
            expected_terms = [
                f"{frac_from(coef)}x^{ne}"
                for ne, coef in sorted(antideriv.items(), reverse=True)
            ]
            expected = " + ".join(expected_terms) + " + C"
            self.assertEqual(solution, expected)


class ConfidenceIntervalTests(TypeabilityMixin, TestCase):
    PROBLEM = re.compile(
        rf"mean (?P<mean>{INT}), standard deviation (?P<s>{INT}), and size "
        rf"n = (?P<n>\d+)\. Using the critical value z = (?P<z>{NUM})"
    )
    SOLUTION = re.compile(rf"\((?P<low>{NUM}), (?P<high>{NUM})\)")

    def test_confidence_interval(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["confidence_interval"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            self._assert_typeable(problem, solution)
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            mean = int(m.group("mean"))
            s = int(m.group("s"))
            n = int(m.group("n"))
            z = float(m.group("z"))
            margin = z * s / math.sqrt(n)
            sol = self.SOLUTION.search(solution)
            self.assertIsNotNone(sol, f"could not parse solution: {solution!r}")
            low, high = float(sol.group("low")), float(sol.group("high"))
            self.assertLess(low, high, f"endpoints out of order: {solution!r}")
            self.assertAlmostEqual(low, round(mean - margin, 3), places=3)
            self.assertAlmostEqual(high, round(mean + margin, 3), places=3)


class QuadraticEquationTests(TypeabilityMixin, TestCase):
    PROBLEM = re.compile(
        r"equation (?P<a>\d+)x\^2 (?P<bs>[+-]) (?P<b>\d+)x "
        r"(?P<cs>[+-]) (?P<c>\d+) = 0"
    )
    SOLUTION = re.compile(rf"(?P<r1>{FRAC}), (?P<r2>{FRAC})")

    def test_quadratic(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["quadratic_equation"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            self._assert_typeable(problem, solution)
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a = int(m.group("a"))
            b = int(m.group("b")) * (1 if m.group("bs") == "+" else -1)
            c = int(m.group("c")) * (1 if m.group("cs") == "+" else -1)

            s = self.SOLUTION.search(solution)
            self.assertIsNotNone(s, f"could not parse solution: {solution!r}")
            r1 = _parse_frac(s.group("r1"))
            r2 = _parse_frac(s.group("r2"))
            self.assertLessEqual(r1, r2, f"roots out of order: {solution!r}")
            # Each stated root must satisfy a x^2 + b x + c = 0 exactly.
            for r in (r1, r2):
                self.assertEqual(a * r * r + b * r + c, 0, f"{r} not a root")
