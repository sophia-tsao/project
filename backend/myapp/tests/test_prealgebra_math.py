"""Math-correctness tests for the pre-algebra generators.

Each test parses the generated problem, recomputes the expected answer
independently, and asserts the generator's stated solution matches. Every
generator is exercised over 2000 random samples under a fixed seed.
"""
import math
import re
from fractions import Fraction

from django.test import TestCase

from myapp.generators import prealgebra  # noqa: F401 - registers pre_* gens
from myapp.generators import LOCAL_GENERATORS

SAMPLES = 2000

# Inequality relation tokens and their reversal. Problems render LaTeX
# (``\leq``/``\geq``); solutions use typeable ASCII (``<=``/``>=``).
FLIP = {"<": ">", ">": "<", "\\leq": "\\geq", "\\geq": "\\leq"}
OP_RE = r"(?:<|>|\\leq|\\geq)"          # relation as it appears in the problem
ASCII_OF = {"<": "<", ">": ">", "\\leq": "<=", "\\geq": ">="}
SOL_OP_RE = r"(?:<=|>=|<|>)"            # relation as it appears in the solution


def parse_frac_solution(solution):
    """Parse a typeable ``$p/q$`` or ``$n$`` solution into a ``Fraction``."""
    m = re.search(r"\$(-?\d+)/(-?\d+)\$", solution)
    if m:
        return Fraction(int(m.group(1)), int(m.group(2)))
    m = re.search(r"\$(-?\d+)\$", solution)
    return Fraction(int(m.group(1)))


# Polynomial term: optional sign, optional magnitude, optional x / x^n.
_TERM = re.compile(r"([+-]?)(\d*)x\^(\d+)|([+-]?)(\d*)x(?!\^)|([+-]?\d+)(?!x)")


def parse_poly(poly):
    terms = []
    for m in _TERM.finditer(poly):
        if m.group(3) is not None:
            sign = -1 if m.group(1) == "-" else 1
            mag = int(m.group(2)) if m.group(2) else 1
            terms.append((sign * mag, int(m.group(3))))
        elif m.group(0).endswith("x"):
            sign = -1 if m.group(4) == "-" else 1
            mag = int(m.group(5)) if m.group(5) else 1
            terms.append((sign * mag, 1))
        elif m.group(6):
            terms.append((int(m.group(6)), 0))
    return terms


def normalize_sci(fr):
    """Same convention as the generator: mantissa in [1,10), 3 dp; int exp."""
    ten = Fraction(10)
    x = fr
    exp = 0
    while x >= ten:
        x /= ten
        exp += 1
    while x < 1:
        x *= ten
        exp -= 1
    return round(float(x), 3), exp


class UnitRateTests(TestCase):
    def test(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["pre_unit_rate"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = re.search(r"travels \$(\d+)\$ miles in \$(\d+)\$ hours", problem)
            d, t = int(m.group(1)), int(m.group(2))
            self.assertEqual(d % t, 0)
            self.assertEqual(int(re.search(r"\$(-?\d+)\$", solution).group(1)), d // t)


class EquivalentRatioTests(TestCase):
    def test(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["pre_equivalent_ratio"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = re.search(r"\$(\d+):(\d+) = (\d+):\\square\$", problem)
            a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
            d = int(re.search(r"\$(\d+)\$", solution).group(1))
            # a/b == c/d
            self.assertEqual(a * d, b * c)


class SolveProportionTests(TestCase):
    def test(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["pre_solve_proportion"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = re.search(r"\\frac\{(\d+)\}\{(\d+)\} = \\frac\{x\}\{(\d+)\}", problem)
            a, b, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            x = int(re.search(r"\$(-?\d+)\$", solution).group(1))
            self.assertEqual(a * d, b * x)


class IntegerOperationsTests(TestCase):
    def test(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["pre_integer_operations"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = re.search(r"\((-?\d+)\) (\+|-|\\times|\\div) \((-?\d+)\)", problem)
            a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
            if op == "+":
                expected = a + b
            elif op == "-":
                expected = a - b
            elif op == "\\times":
                expected = a * b
            else:
                self.assertEqual(a % b, 0)
                expected = a // b
            result = int(re.search(r"\$(-?\d+)\$", solution).group(1))
            self.assertEqual(result, expected)


class RationalOperationsTests(TestCase):
    def test(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["pre_rational_operations"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = re.search(
                r"\\frac\{(-?\d+)\}\{(\d+)\} (\+|-|\\times|\\div) "
                r"\\frac\{(-?\d+)\}\{(\d+)\}",
                problem,
            )
            f1 = Fraction(int(m.group(1)), int(m.group(2)))
            f2 = Fraction(int(m.group(4)), int(m.group(5)))
            op = m.group(3)
            if op == "+":
                expected = f1 + f2
            elif op == "-":
                expected = f1 - f2
            elif op == "\\times":
                expected = f1 * f2
            else:
                expected = f1 / f2
            self.assertEqual(parse_frac_solution(solution), expected)


class AbsoluteValueTests(TestCase):
    def test(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["pre_absolute_value"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            result = int(re.search(r"\$(-?\d+)\$", solution).group(1))
            m = re.search(r"\|(-?\d+) - (-?\d+)\|", problem)
            if m:
                expected = abs(int(m.group(1)) - int(m.group(2)))
            else:
                m2 = re.search(r"\|(-?\d+)\| \+ \|(-?\d+)\|", problem)
                expected = abs(int(m2.group(1))) + abs(int(m2.group(2)))
            self.assertEqual(result, expected)


class OneStepInequalityTests(TestCase):
    def test(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["pre_one_step_inequality"]
        sol_re = re.compile(rf"x ({SOL_OP_RE}) (-?\d+)")
        for _ in range(SAMPLES):
            problem, solution = gen()
            sm = sol_re.search(solution)
            sol_op, sol_c = sm.group(1), int(sm.group(2))

            add = re.search(rf"x ([+-]) (\d+) ({OP_RE}) (-?\d+)", problem)
            mul = re.search(rf"(-?\d+)x ({OP_RE}) (-?\d+)", problem)
            if add:
                a = int(add.group(2)) * (1 if add.group(1) == "+" else -1)
                op = add.group(3)
                b = int(add.group(4))
                self.assertEqual(sol_op, ASCII_OF[op])
                self.assertEqual(sol_c, b - a)
            else:
                k = int(mul.group(1))
                op = mul.group(2)
                b = int(mul.group(3))
                self.assertEqual(b % k, 0)
                expected_op = FLIP[op] if k < 0 else op
                self.assertEqual(sol_op, ASCII_OF[expected_op])
                self.assertEqual(sol_c, b // k)


class MultiStepInequalityTests(TestCase):
    def test(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["pre_multi_step_inequality"]
        sol_re = re.compile(rf"x ({SOL_OP_RE}) (-?\d+)")
        prob_re = re.compile(rf"(-?\d+)x ([+-]) (\d+) ({OP_RE}) (-?\d+)")
        for _ in range(SAMPLES):
            problem, solution = gen()
            sm = sol_re.search(solution)
            sol_op, sol_c = sm.group(1), int(sm.group(2))
            pm = prob_re.search(problem)
            a = int(pm.group(1))
            b = int(pm.group(3)) * (1 if pm.group(2) == "+" else -1)
            op = pm.group(4)
            c = int(pm.group(5))
            self.assertEqual((c - b) % a, 0)
            expected_op = FLIP[op] if a < 0 else op
            self.assertEqual(sol_op, ASCII_OF[expected_op])
            self.assertEqual(sol_c, (c - b) // a)


class ScientificNotationTests(TestCase):
    def test(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["pre_scientific_notation_ops"]
        ten = Fraction(10)
        prob_re = re.compile(
            r"(\d+\.\d) \\times 10\^\{(-?\d+)\} (\+|-|\\div) "
            r"(\d+\.\d) \\times 10\^\{(-?\d+)\}"
        )
        sol_re = re.compile(r"\$([\d.]+)\*10\^(-?\d+)\$")
        for _ in range(SAMPLES):
            problem, solution = gen()
            pm = prob_re.search(problem)
            m1 = Fraction(pm.group(1))
            e1 = int(pm.group(2))
            op = pm.group(3)
            m2 = Fraction(pm.group(4))
            e2 = int(pm.group(5))
            f1 = m1 * (ten ** e1)
            f2 = m2 * (ten ** e2)
            if op == "+":
                value = f1 + f2
            elif op == "-":
                value = f1 - f2
            else:
                value = f1 / f2
            mant, exp = normalize_sci(value)
            sm = sol_re.search(solution)
            self.assertAlmostEqual(float(sm.group(1)), mant, places=3)
            self.assertEqual(int(sm.group(2)), exp)


class IntegerExponentRulesTests(TestCase):
    def test(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["pre_integer_exponent_rules"]
        sol_re = re.compile(r"\$(\d+)\^(-?\d+)\$")
        for _ in range(SAMPLES):
            problem, solution = gen()
            sm = sol_re.search(solution)
            base, r = int(sm.group(1)), int(sm.group(2))
            mult = re.search(r"(\d+)\^\{(-?\d+)\} \\times (\d+)\^\{(-?\d+)\}", problem)
            div = re.search(r"(\d+)\^\{(-?\d+)\} \\div (\d+)\^\{(-?\d+)\}", problem)
            power = re.search(r"\((\d+)\^\{(-?\d+)\}\)\^\{(-?\d+)\}", problem)
            if mult:
                self.assertEqual(int(mult.group(1)), base)
                self.assertEqual(int(mult.group(3)), base)
                self.assertEqual(r, int(mult.group(2)) + int(mult.group(4)))
            elif div:
                self.assertEqual(r, int(div.group(2)) - int(div.group(4)))
            else:
                self.assertEqual(r, int(power.group(2)) * int(power.group(3)))


class ConstantOfProportionalityTests(TestCase):
    def test(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["pre_constant_of_proportionality"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = re.search(r"When \$x = (-?\d+)\$, \$y = (-?\d+)\$", problem)
            x, y = int(m.group(1)), int(m.group(2))
            k = int(re.search(r"\$(-?\d+)\$", solution).group(1))
            self.assertEqual(k * x, y)


class EvaluateFunctionTests(TestCase):
    def test(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["pre_evaluate_function"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = re.search(r"f\(x\)=(.+?)\$, evaluate \$f\((-?\d+)\)", problem)
            terms = parse_poly(m.group(1))
            v = int(m.group(2))
            expected = sum(coeff * (v ** exp) for coeff, exp in terms)
            result = int(re.search(r"\$(-?\d+)\$", solution).group(1))
            self.assertEqual(result, expected)


class SlopeFromTwoPointsTests(TestCase):
    def test(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["pre_slope_from_two_points"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = re.search(
                r"\$\((-?\d+), (-?\d+)\)\$ and \$\((-?\d+), (-?\d+)\)\$", problem
            )
            x1, y1, x2, y2 = (int(m.group(i)) for i in range(1, 5))
            self.assertNotEqual(x1, x2)
            expected = Fraction(y2 - y1, x2 - x1)
            self.assertEqual(parse_frac_solution(solution), expected)


class LinearFunctionValueTests(TestCase):
    def test(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["pre_linear_function_value"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = re.search(
                r"slope \$m = (-?\d+)\$ and y-intercept \$b = (-?\d+)\$\. "
                r"Find \$y\$ when \$x = (-?\d+)\$",
                problem,
            )
            mm, b, x = int(m.group(1)), int(m.group(2)), int(m.group(3))
            y = int(re.search(r"\$(-?\d+)\$", solution).group(1))
            self.assertEqual(y, mm * x + b)


class MeanAbsoluteDeviationTests(TestCase):
    def test(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["pre_mean_absolute_deviation"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = re.search(r"data set: \$([\d, ]+)\$", problem)
            data = [int(v) for v in m.group(1).split(", ")]
            mean = sum(data) / len(data)
            expected = round(sum(abs(v - mean) for v in data) / len(data), 3)
            stated = float(re.search(r"\$([\d.]+)\$", solution).group(1))
            self.assertAlmostEqual(stated, expected, places=3)


class InterquartileRangeTests(TestCase):
    def test(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["pre_interquartile_range"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = re.search(r"data set: \$([\d, ]+)\$", problem)
            data = sorted(int(v) for v in m.group(1).split(", "))
            self.assertEqual(len(data), 7)
            expected = data[5] - data[1]  # Q3 - Q1
            stated = int(re.search(r"\$(-?\d+)\$", solution).group(1))
            self.assertEqual(stated, expected)


class ApproximateIrrationalTests(TestCase):
    def test(self):
        import random
        random.seed(0)
        gen = LOCAL_GENERATORS["pre_approximate_irrational"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            n = int(re.search(r"\\sqrt\{(\d+)\}", problem).group(1))
            root = math.sqrt(n)
            self.assertNotEqual(root, int(root))  # not a perfect square
            expected = round(root, 1)
            stated = float(re.search(r"\$([\d.]+)\$", solution).group(1))
            self.assertAlmostEqual(stated, expected, places=3)
