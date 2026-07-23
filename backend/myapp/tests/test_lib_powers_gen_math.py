"""Math-correctness tests for the ``lib_powers_gen`` library overrides.

Each generator is exercised over many samples under a fixed seed: the problem
statement is parsed, the expected answer is recomputed independently, and the
generator's stated solution is asserted to match. Every solution is also checked
against the strict typeability rules (no LaTeX, no untypeable sci-notation, no
>3-decimal numbers).
"""
import random
import re
from fractions import Fraction

from django.test import TestCase

from myapp.generators import lib_powers_gen  # noqa: F401 - registers generators
from myapp.generators import LOCAL_GENERATORS

SAMPLES = 500


def assert_typeable(test, solution):
    """Assert a solution string contains no banned/untypeable tokens."""
    test.assertNotIn("\\", solution, f"backslash in {solution!r}")
    test.assertNotIn("{", solution, f"brace in {solution!r}")
    test.assertNotIn("}", solution, f"brace in {solution!r}")
    test.assertNotIn("[", solution, f"bracket in {solution!r}")
    test.assertNotIn("]", solution, f"bracket in {solution!r}")
    for tok in ("\\frac", "\\sqrt", "\\times", "\\cdot",
                "\\geq", "\\leq", "\\neq"):
        test.assertNotIn(tok, solution, f"{tok} in {solution!r}")
    # No scientific-notation float form like 2.9e-11.
    test.assertIsNone(
        re.search(r"\d[eE][-+]?\d", solution),
        f"e-notation float in {solution!r}",
    )
    # No number with more than 3 decimal places.
    test.assertIsNone(
        re.search(r"\d\.\d{4,}", solution),
        f">3-decimal number in {solution!r}",
    )
    # No trailing .0 style whole numbers.
    test.assertIsNone(
        re.search(r"\d\.0\b", solution),
        f"trailing .0 in {solution!r}",
    )


def assert_problem_clean(test, problem):
    """Problem text must have balanced $ and no backslash (no raw LaTeX)."""
    test.assertNotIn("\\", problem, f"backslash in {problem!r}")
    test.assertEqual(problem.count("$") % 2, 0, f"unbalanced $ in {problem!r}")


class SystemOfEquationsTests(TestCase):
    EQ = re.compile(r"\$(-?\d+)x([+-]\d+)y=(-?\d+)\$")
    SOL = re.compile(r"^x=(-?\d+), y=(-?\d+)$")

    def test_solution_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["system_of_equations"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            assert_problem_clean(self, problem)
            assert_typeable(self, solution)
            eqs = self.EQ.findall(problem)
            self.assertEqual(len(eqs), 2, f"could not parse: {problem!r}")
            (a, b, e), (c, d, f) = (
                (int(x), int(y), int(z)) for x, y, z in eqs
            )
            det = a * d - b * c
            self.assertNotEqual(det, 0, problem)
            # Cramer's rule -> unique solution.
            exp_x = Fraction(e * d - b * f, det)
            exp_y = Fraction(a * f - e * c, det)
            m = self.SOL.match(solution)
            self.assertIsNotNone(m, f"bad format: {solution!r}")
            self.assertEqual(Fraction(int(m.group(1))), exp_x, problem)
            self.assertEqual(Fraction(int(m.group(2))), exp_y, problem)


class CombineLikeTermsTests(TestCase):
    TERM = re.compile(r"(\d+)x\^\{(\d+)\}")
    # Solution terms: coeff optional, x, ^power optional.
    SOL_TERM = re.compile(r"^(\d*)x(?:\^(\d+))?$")

    def test_combined_and_ordered(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["combine_like_terms"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            assert_problem_clean(self, problem)
            assert_typeable(self, solution)

            # Sum coefficients per power from the unsimplified problem sum.
            body = problem.split("$")[1]
            expected = {}
            for coeff, power in self.TERM.findall(body):
                p = int(power)
                expected[p] = expected.get(p, 0) + int(coeff)

            # Parse the solution terms.
            parts = [p.strip() for p in solution.split("+")]
            powers_seen = []
            parsed = {}
            for part in parts:
                m = self.SOL_TERM.match(part)
                self.assertIsNotNone(m, f"bad term {part!r} in {solution!r}")
                coeff_txt, power_txt = m.group(1), m.group(2)
                # No leading "1" coefficient (write x, not 1x).
                self.assertNotEqual(coeff_txt, "1",
                                    f"unit coeff shown: {solution!r}")
                coeff = int(coeff_txt) if coeff_txt else 1
                # No "^1" (write x, not x^1).
                self.assertNotEqual(power_txt, "1",
                                    f"^1 shown: {solution!r}")
                power = int(power_txt) if power_txt else 1
                parsed[power] = coeff
                powers_seen.append(power)

            # Strictly descending power order.
            self.assertEqual(powers_seen, sorted(powers_seen, reverse=True),
                             f"not descending: {solution!r}")
            self.assertEqual(len(powers_seen), len(set(powers_seen)),
                             f"duplicate powers: {solution!r}")
            self.assertEqual(parsed, expected,
                             f"coeffs wrong: {problem!r} -> {solution!r}")


class PowerOfPowersTests(TestCase):
    PROBLEM = re.compile(r"\$\((\d+)\^\{(\d+)\}\)\^\{(\d+)\}\$")
    SOL = re.compile(r"^(\d+)\^(\d+)$")

    def test_product_of_exponents(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["power_of_powers"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            assert_problem_clean(self, problem)
            assert_typeable(self, solution)
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a, exp_m, n = (int(x) for x in m.groups())
            s = self.SOL.match(solution)
            self.assertIsNotNone(s, f"bad format: {solution!r}")
            self.assertEqual(int(s.group(1)), a, problem)
            self.assertEqual(int(s.group(2)), exp_m * n, problem)


class QuotientSameBaseTests(TestCase):
    PROBLEM = re.compile(r"\$(\d+)\^\{(\d+)\} / (\d+)\^\{(\d+)\}\$")
    SOL = re.compile(r"^(\d+)\^(\d+)$")

    def test_difference_of_exponents(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["quotient_of_power_same_base"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            assert_problem_clean(self, problem)
            assert_typeable(self, solution)
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a1, exp_m, a2, exp_n = (int(x) for x in m.groups())
            self.assertEqual(a1, a2, problem)
            self.assertGreater(exp_m, exp_n, problem)
            s = self.SOL.match(solution)
            self.assertIsNotNone(s, f"bad format: {solution!r}")
            self.assertEqual(int(s.group(1)), a1, problem)
            self.assertEqual(int(s.group(2)), exp_m - exp_n, problem)


class QuotientSamePowerTests(TestCase):
    PROBLEM = re.compile(r"\$(\d+)\^\{(\d+)\} / (\d+)\^\{(\d+)\}\$")
    SOL_FRAC = re.compile(r"^\((\d+)/(\d+)\)\^(\d+)$")
    SOL_WHOLE = re.compile(r"^(\d+)\^(\d+)$")

    def test_ratio_base(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["quotient_of_power_same_power"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            assert_problem_clean(self, problem)
            assert_typeable(self, solution)
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a, n1, b, n2 = (int(x) for x in m.groups())
            self.assertEqual(n1, n2, problem)
            expected = Fraction(a, b)
            fm = self.SOL_FRAC.match(solution)
            wm = self.SOL_WHOLE.match(solution)
            if expected.denominator == 1:
                self.assertIsNotNone(wm, f"expected k^n: {solution!r}")
                self.assertEqual(int(wm.group(1)), expected.numerator, problem)
                self.assertEqual(int(wm.group(2)), n1, problem)
            else:
                self.assertIsNotNone(fm, f"expected (a/b)^n: {solution!r}")
                self.assertEqual(
                    Fraction(int(fm.group(1)), int(fm.group(2))),
                    expected, problem)
                self.assertEqual(int(fm.group(3)), n1, problem)


class ProductScientificTests(TestCase):
    PROBLEM = re.compile(
        r"\(([\d.]+)\*10\^(-?\d+)\)\(([\d.]+)\*10\^(-?\d+)\)"
    )
    SOL = re.compile(r"^([\d.]+)\*10\^(-?\d+)$")

    def test_product_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["product_of_scientific_notations"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            assert_problem_clean(self, problem)
            assert_typeable(self, solution)
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a = Fraction(m.group(1))
            p = int(m.group(2))
            b = Fraction(m.group(3))
            q = int(m.group(4))

            mantissa = a * b
            exponent = p + q
            if mantissa >= 10:
                mantissa /= 10
                exponent += 1

            s = self.SOL.match(solution)
            self.assertIsNotNone(s, f"bad format: {solution!r}")
            # Mantissa should be normalised to [1, 10) (allowing 3dp rounding).
            self.assertGreaterEqual(float(s.group(1)), 1.0, solution)
            self.assertLess(float(s.group(1)), 10.0, solution)
            self.assertEqual(int(s.group(2)), exponent, problem)
            self.assertAlmostEqual(
                float(s.group(1)), round(float(mantissa), 3), places=3,
                msg=f"{problem!r} -> {solution!r}")
