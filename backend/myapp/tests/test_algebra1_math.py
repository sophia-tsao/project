"""Math-correctness tests for the Algebra: Concepts & Connections generators.

Each test parses the generated problem statement, independently recomputes the
expected answer, and asserts the generator's stated solution matches. Every
generator is exercised over many random samples under a fixed seed so the check
covers its whole input space deterministically.
"""
import random
import re
from fractions import Fraction

from django.test import TestCase

from myapp.generators import algebra1  # noqa: F401 - registers the generators
from myapp.generators import LOCAL_GENERATORS

SAMPLES = 2000


def _frac(text):
    """Parse ``'n'`` or ``'p/q'`` into a Fraction."""
    text = text.strip()
    if "/" in text:
        num, den = text.split("/")
        return Fraction(int(num), int(den))
    return Fraction(int(text))


class AbsoluteValueEquationTests(TestCase):
    PROBLEM = re.compile(r"\|(?P<a>\d+)x(?P<b>[+-]\d+)?\|=(?P<c>-?\d+)")
    ROOT = re.compile(r"x = (-?\d+(?:/\d+)?)")

    def test_roots_match(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["alg1_absolute_value_equation"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a = int(m.group("a"))
            b = int(m.group("b")) if m.group("b") else 0
            c = int(m.group("c"))

            if c < 0:
                self.assertEqual(solution, "no solution", problem)
                continue

            expected = {Fraction(c - b, a), Fraction(-c - b, a)}
            stated = {_frac(t) for t in self.ROOT.findall(solution)}
            self.assertEqual(
                stated, expected,
                f"roots wrong for {problem!r} -> {solution!r}",
            )


class ExponentialGrowthDecayTests(TestCase):
    PROBLEM = re.compile(
        r"amount of \$(?P<p>\d+)\$ (?P<verb>grows|decays) at a rate of "
        r"\$(?P<rate>\d+)\\%\$ per period. Find the amount after "
        r"\$(?P<n>\d+)\$ periods"
    )
    SOLUTION = re.compile(r"\$(?P<amt>-?[\d.]+)\$")

    def test_final_amount_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["alg1_exponential_growth_decay"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            principal = int(m.group("p"))
            rate = int(m.group("rate"))
            periods = int(m.group("n"))
            factor = (
                1 + rate / 100 if m.group("verb") == "grows" else 1 - rate / 100
            )
            expected = principal * factor ** periods
            stated = float(self.SOLUTION.search(solution).group("amt"))
            self.assertAlmostEqual(
                stated, expected, places=2,
                msg=f"amount wrong for {problem!r} -> {solution!r}",
            )


class EvaluateExponentialTests(TestCase):
    PROBLEM = re.compile(
        r"f\(x\)=(?P<a>\d+) \\cdot (?P<b>\d+)\^x\$, evaluate \$f\((?P<x>-?\d+)\)"
    )
    SOLUTION = re.compile(r"\$(?P<val>-?\d+(?:/\d+)?)\$")

    def test_value_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["alg1_evaluate_exponential"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a = int(m.group("a"))
            b = int(m.group("b"))
            x = int(m.group("x"))
            expected = Fraction(a) * Fraction(b) ** x
            stated = _frac(self.SOLUTION.search(solution).group("val"))
            self.assertEqual(
                stated, expected,
                f"value wrong for {problem!r} -> {solution!r}",
            )


class DomainOfFunctionTests(TestCase):
    SQRT = re.compile(r"\\sqrt\{x(?P<b>[+-]\d+)?\}")
    RATIONAL = re.compile(r"\\frac\{1\}\{x(?P<b>[+-]\d+)?\}")
    GEQ = re.compile(r"x >= (?P<v>-?\d+)")
    NEQ = re.compile(r"x != (?P<v>-?\d+)")

    def test_domain_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["alg1_domain_of_function"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            sqrt = self.SQRT.search(problem)
            rational = self.RATIONAL.search(problem)
            if sqrt is not None:
                b = int(sqrt.group("b")) if sqrt.group("b") else 0
                m = self.GEQ.search(solution)
                self.assertIsNotNone(m, f"expected >= for {problem!r}")
                self.assertEqual(int(m.group("v")), -b, problem)
            else:
                self.assertIsNotNone(rational, f"could not parse: {problem!r}")
                b = int(rational.group("b")) if rational.group("b") else 0
                m = self.NEQ.search(solution)
                self.assertIsNotNone(m, f"expected != for {problem!r}")
                self.assertEqual(int(m.group("v")), -b, problem)


class DiscriminantTests(TestCase):
    PROBLEM = re.compile(r"discriminant of \$(?P<quad>[^$]+)\$")
    SOLUTION = re.compile(r"D=(?P<d>-?\d+)\$, (?P<n>\d+) real")

    def test_discriminant_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["alg1_discriminant"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            quad = self.PROBLEM.search(problem).group("quad")
            a, b, c = _parse_quad(quad)
            expected_d = b * b - 4 * a * c
            expected_n = 2 if expected_d > 0 else (1 if expected_d == 0 else 0)
            m = self.SOLUTION.search(solution)
            self.assertIsNotNone(m, f"could not parse: {solution!r}")
            self.assertEqual(int(m.group("d")), expected_d, problem)
            self.assertEqual(int(m.group("n")), expected_n, problem)


class AxisOfSymmetryTests(TestCase):
    PROBLEM = re.compile(r"axis of symmetry of \$(?P<quad>[^$]+)\$")
    SOLUTION = re.compile(r"x = (?P<v>-?\d+(?:/\d+)?)")

    def test_axis_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["alg1_axis_of_symmetry"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            quad = self.PROBLEM.search(problem).group("quad")
            a, b, c = _parse_quad(quad)
            expected = Fraction(-b, 2 * a)
            stated = _frac(self.SOLUTION.search(solution).group("v"))
            self.assertEqual(
                stated, expected,
                f"axis wrong for {problem!r} -> {solution!r}",
            )


class SumProductRootsTests(TestCase):
    PROBLEM = re.compile(r"For \$(?P<quad>[^$]+)\$")
    SOLUTION = re.compile(
        r"sum=(?P<s>-?\d+(?:/\d+)?), product=(?P<p>-?\d+(?:/\d+)?)"
    )

    def test_sum_and_product_match(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["alg1_sum_product_roots"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            quad = self.PROBLEM.search(problem).group("quad")
            a, b, c = _parse_quad(quad)
            expected_sum = Fraction(-b, a)
            expected_product = Fraction(c, a)
            m = self.SOLUTION.search(solution)
            self.assertIsNotNone(m, f"could not parse: {solution!r}")
            self.assertEqual(_frac(m.group("s")), expected_sum, problem)
            self.assertEqual(_frac(m.group("p")), expected_product, problem)


class LinearInequalityTests(TestCase):
    PROBLEM = re.compile(
        r"\$(?P<a>-?\d+)x(?P<b>[+-]\d+)? (?P<op>\S+) (?P<c>-?\d+)\$"
    )
    # Solutions render relations in typeable ASCII; problems keep LaTeX.
    SOLUTION = re.compile(r"x (?P<op><=|>=|<|>) (?P<v>-?\d+(?:/\d+)?)")
    FLIP = {"<": ">", ">": "<", "\\leq": "\\geq", "\\geq": "\\leq"}
    ASCII_OF = {"<": "<", ">": ">", "\\leq": "<=", "\\geq": ">="}

    def test_inequality_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["alg1_linear_inequality_solve"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a = int(m.group("a"))
            b = int(m.group("b")) if m.group("b") else 0
            c = int(m.group("c"))
            op = m.group("op")
            expected_threshold = Fraction(c - b, a)
            expected_op = self.FLIP[op] if a < 0 else op

            sol = self.SOLUTION.search(solution)
            self.assertIsNotNone(sol, f"could not parse: {solution!r}")
            self.assertEqual(sol.group("op"), self.ASCII_OF[expected_op], problem)
            self.assertEqual(
                _frac(sol.group("v")), expected_threshold,
                f"threshold wrong for {problem!r} -> {solution!r}",
            )


# Strict quadratic parser for "ax^2+bx+c" strings (a != 0), handling omitted
# unit/zero coefficients exactly as alg1._quadratic renders them.
_QUAD_RE = re.compile(
    r"^(?P<a>-?\d*)x\^2"
    r"(?:(?P<bsign>[+-])(?P<bmag>\d*)x)?"
    r"(?:(?P<csign>[+-])(?P<cmag>\d+))?$"
)


def _parse_quad(text):
    m = _QUAD_RE.match(text.strip())
    assert m is not None, f"could not parse quadratic: {text!r}"
    a_raw = m.group("a")
    a = 1 if a_raw == "" else (-1 if a_raw == "-" else int(a_raw))
    if m.group("bsign") is None:
        b = 0
    else:
        mag = int(m.group("bmag")) if m.group("bmag") else 1
        b = mag if m.group("bsign") == "+" else -mag
    if m.group("csign") is None:
        c = 0
    else:
        c = int(m.group("cmag")) if m.group("csign") == "+" else -int(m.group("cmag"))
    return a, b, c
