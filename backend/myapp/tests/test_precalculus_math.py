"""Math-correctness tests for the Georgia "Precalculus" generators.

Each test parses the generated problem statement, independently recomputes the
expected answer, and asserts the generator's stated solution matches. Run over
many random samples so the check covers the whole input space.
"""
import math
import random
import re
from fractions import Fraction

from django.test import TestCase

from myapp.generators import precalculus  # noqa: F401  (registers generators)
from myapp.generators import LOCAL_GENERATORS

SAMPLES = 2000


# Map special-value LaTeX tokens back to their numeric values.
_SPECIAL = {
    r"0": 0.0,
    r"\frac{1}{2}": 0.5,
    r"\frac{\sqrt{2}}{2}": math.sqrt(2) / 2,
    r"\frac{\sqrt{3}}{2}": math.sqrt(3) / 2,
    r"1": 1.0,
    r"-\frac{1}{2}": -0.5,
    r"-\frac{\sqrt{2}}{2}": -math.sqrt(2) / 2,
    r"-\frac{\sqrt{3}}{2}": -math.sqrt(3) / 2,
    r"-1": -1.0,
    r"\frac{\sqrt{3}}{3}": math.sqrt(3) / 3,
    r"\sqrt{3}": math.sqrt(3),
    r"-\frac{\sqrt{3}}{3}": -math.sqrt(3) / 3,
    r"-\sqrt{3}": -math.sqrt(3),
}


class LawOfSinesTests(TestCase):
    PROBLEM = re.compile(
        r"angle \$A = (?P<A>\d+)\^\\circ\$, angle \$B = (?P<B>\d+)\^\\circ\$, "
        r"and side \$a = (?P<a>\d+)\$"
    )
    SOLUTION = re.compile(r"\$(?P<ans>-?[\d.]+)\$")

    def test_side_matches_law_of_sines(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["pc_law_of_sines"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            A, B, a = int(m.group("A")), int(m.group("B")), int(m.group("a"))
            expected = a * math.sin(math.radians(B)) / math.sin(math.radians(A))
            stated = float(self.SOLUTION.search(solution).group("ans"))
            self.assertAlmostEqual(stated, expected, places=3,
                                   msg=f"{problem!r} -> {solution!r}")


class LawOfCosinesSideTests(TestCase):
    PROBLEM = re.compile(
        r"side \$a = (?P<a>\d+)\$, side \$b = (?P<b>\d+)\$, and the included "
        r"angle \$C = (?P<C>\d+)\^\\circ\$"
    )
    SOLUTION = re.compile(r"\$(?P<ans>-?[\d.]+)\$")

    def test_third_side_matches_law_of_cosines(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["pc_law_of_cosines_side"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a, b, C = int(m.group("a")), int(m.group("b")), int(m.group("C"))
            expected = math.sqrt(a * a + b * b - 2 * a * b * math.cos(math.radians(C)))
            stated = float(self.SOLUTION.search(solution).group("ans"))
            self.assertAlmostEqual(stated, expected, places=3,
                                   msg=f"{problem!r} -> {solution!r}")


class ObliqueTriangleAreaTests(TestCase):
    PROBLEM = re.compile(
        r"sides \$a = (?P<a>\d+)\$ and \$b = (?P<b>\d+)\$ with included angle "
        r"\$C = (?P<C>\d+)\^\\circ\$"
    )
    SOLUTION = re.compile(r"\$(?P<ans>-?[\d.]+)\$")

    def test_area_matches_sas_formula(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["pc_oblique_triangle_area"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a, b, C = int(m.group("a")), int(m.group("b")), int(m.group("C"))
            expected = 0.5 * a * b * math.sin(math.radians(C))
            stated = float(self.SOLUTION.search(solution).group("ans"))
            self.assertAlmostEqual(stated, expected, places=3,
                                   msg=f"{problem!r} -> {solution!r}")


class InverseTrigTests(TestCase):
    PROBLEM = re.compile(r"\\arc(?P<func>sin|cos|tan)\\left\((?P<val>.+?)\\right\)")
    SOLUTION = re.compile(r"\$(?P<deg>-?\d+)\$")

    def test_inverse_trig_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["pc_inverse_trig"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            func = m.group("func")
            value = _SPECIAL[m.group("val")]
            if func == "sin":
                expected = math.degrees(math.asin(value))
            elif func == "cos":
                expected = math.degrees(math.acos(value))
            else:
                expected = math.degrees(math.atan(value))
            deg = int(self.SOLUTION.search(solution).group("deg"))
            self.assertAlmostEqual(deg, expected, places=3,
                                   msg=f"{problem!r} -> {solution!r}")


class DoubleAngleTests(TestCase):
    PROBLEM = re.compile(
        r"\\(?P<given>sin|cos) x = \\frac\{(?P<num>\d+)\}\{(?P<den>\d+)\}.*?"
        r"find \$\\(?P<target>sin|cos)\(2x\)"
    )
    FRAC = re.compile(r"\$(?P<n>-?\d+)/(?P<d>-?\d+)\$")

    def test_double_angle_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["pc_double_angle"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            given, num, den = m.group("given"), int(m.group("num")), int(m.group("den"))
            target = m.group("target")
            # x acute: recover both sin and cos from the Pythagorean identity.
            if given == "sin":
                sin_v = num / den
                cos_v = math.sqrt(1 - sin_v * sin_v)
            else:
                cos_v = num / den
                sin_v = math.sqrt(1 - cos_v * cos_v)
            if target == "sin":
                expected = 2 * sin_v * cos_v
            else:
                expected = cos_v * cos_v - sin_v * sin_v
            fr = self.FRAC.search(solution)
            self.assertIsNotNone(fr, f"could not parse solution: {solution!r}")
            stated = int(fr.group("n")) / int(fr.group("d"))
            self.assertAlmostEqual(stated, expected, places=3,
                                   msg=f"{problem!r} -> {solution!r}")

    def test_double_angle_fraction_reduced(self):
        random.seed(1)
        gen = LOCAL_GENERATORS["pc_double_angle"]
        for _ in range(SAMPLES):
            _p, solution = gen()
            fr = self.FRAC.search(solution)
            self.assertEqual(math.gcd(int(fr.group("n")), int(fr.group("d"))), 1,
                             f"fraction not reduced: {solution!r}")


class SolveTrigEquationTests(TestCase):
    PROBLEM = re.compile(r"\\(?P<func>sin|cos|tan)\(x\) = (?P<val>.+?)\$ for \$x\$")
    SOLUTION = re.compile(r"\$(?P<sols>[-\d,\s]*)\$")

    def test_solutions_match(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["pc_solve_trig_equation"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            func = m.group("func")
            value = _SPECIAL[m.group("val")]
            fn = {"sin": math.sin, "cos": math.cos, "tan": math.tan}[func]
            expected = set()
            for d in range(360):
                if func == "tan" and d in (90, 270):
                    continue
                if abs(fn(math.radians(d)) - value) < 1e-6:
                    expected.add(d)
            raw = self.SOLUTION.search(solution).group("sols").strip()
            stated = set(int(s) for s in raw.split(",")) if raw else set()
            self.assertEqual(stated, expected, f"{problem!r} -> {solution!r}")


class PolarToRectangularTests(TestCase):
    PROBLEM = re.compile(
        r"\(r, \\theta\) = \((?P<r>\d+), (?P<theta>\d+)\^\\circ\)"
    )
    SOLUTION = re.compile(r"\((?P<x>-?[\d.]+), (?P<y>-?[\d.]+)\)")

    def test_conversion_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["pc_polar_to_rectangular"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            r, theta = int(m.group("r")), int(m.group("theta"))
            ex = r * math.cos(math.radians(theta))
            ey = r * math.sin(math.radians(theta))
            s = self.SOLUTION.search(solution)
            self.assertAlmostEqual(float(s.group("x")), ex, places=3,
                                   msg=f"{problem!r} -> {solution!r}")
            self.assertAlmostEqual(float(s.group("y")), ey, places=3,
                                   msg=f"{problem!r} -> {solution!r}")


class RectangularToPolarTests(TestCase):
    PROBLEM = re.compile(
        r"\(x, y\) = \((?P<x>-?\d+), (?P<y>-?\d+)\)"
    )
    SOLUTION = re.compile(r"\((?P<r>[\d.]+), (?P<theta>[\d.]+)\)")

    def test_conversion_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["pc_rectangular_to_polar"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            x, y = int(m.group("x")), int(m.group("y"))
            er = math.hypot(x, y)
            et = math.degrees(math.atan2(y, x))
            if et < 0:
                et += 360
            s = self.SOLUTION.search(solution)
            self.assertAlmostEqual(float(s.group("r")), er, places=3,
                                   msg=f"{problem!r} -> {solution!r}")
            self.assertAlmostEqual(float(s.group("theta")), et, places=3,
                                   msg=f"{problem!r} -> {solution!r}")


class FiniteGeometricSumTests(TestCase):
    PROBLEM = re.compile(
        r"first \$(?P<n>\d+)\$ terms .* first term \$a = (?P<a>-?\d+)\$ and "
        r"common ratio \$r = (?P<r>-?\d+)\$"
    )
    SOLUTION = re.compile(r"\$(?P<ans>-?\d+)\$")

    def test_sum_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["pc_finite_geometric_sum"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            n, a, r = int(m.group("n")), int(m.group("a")), int(m.group("r"))
            expected = sum(a * r ** k for k in range(n))
            stated = int(self.SOLUTION.search(solution).group("ans"))
            self.assertEqual(stated, expected, f"{problem!r} -> {solution!r}")


class SigmaArithmeticSumTests(TestCase):
    PROBLEM = re.compile(
        r"\\sum_\{k=1\}\^\{(?P<n>\d+)\} \((?P<coeff>\d+)k(?P<const> [+-] \d+)?\)"
    )
    SOLUTION = re.compile(r"\$(?P<ans>-?\d+)\$")

    def test_sum_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["pc_sigma_arithmetic_sum"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            n = int(m.group("n"))
            coeff = int(m.group("coeff"))
            const_raw = m.group("const")
            const = 0
            if const_raw:
                const = int(const_raw.replace(" ", ""))
            expected = sum(coeff * k + const for k in range(1, n + 1))
            stated = int(self.SOLUTION.search(solution).group("ans"))
            self.assertEqual(stated, expected, f"{problem!r} -> {solution!r}")


class SequenceLimitTests(TestCase):
    PROBLEM = re.compile(
        r"\\frac\{(?P<num>[^{}]+)\}\{(?P<den>[^{}]+)\}"
    )
    INT_SOL = re.compile(r"\$(?P<ans>-?\d+)\$")
    FRAC_SOL = re.compile(r"\$(?P<n>-?\d+)/(?P<d>-?\d+)\$")
    # Highest-degree term of a polynomial in n.
    TERM = re.compile(r"^(?P<sign>-?)(?P<mag>\d*)n(?:\^(?P<exp>\d+))?")

    @classmethod
    def _leading(cls, poly):
        m = cls.TERM.match(poly)
        sign = -1 if m.group("sign") == "-" else 1
        mag = int(m.group("mag")) if m.group("mag") else 1
        return sign * mag

    def test_limit_matches_leading_ratio(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["pc_sequence_limit"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            num_lead = self._leading(m.group("num"))
            den_lead = self._leading(m.group("den"))
            expected = Fraction(num_lead, den_lead)
            fr = self.FRAC_SOL.search(solution)
            if fr:
                stated = Fraction(int(fr.group("n")), int(fr.group("d")))
            else:
                stated = Fraction(int(self.INT_SOL.search(solution).group("ans")))
            self.assertEqual(stated, expected, f"{problem!r} -> {solution!r}")


class VectorAddTests(TestCase):
    PROBLEM = re.compile(
        r"\\vec\{u\} = \\langle (?P<ux>-?\d+), (?P<uy>-?\d+) \\rangle.*?"
        r"\\vec\{v\} = \\langle (?P<vx>-?\d+), (?P<vy>-?\d+) \\rangle.*?"
        r"Compute \$(?P<op>.+?)\$\."
    )
    SOLUTION = re.compile(r"\((?P<x>-?\d+), (?P<y>-?\d+)\)")

    def test_vector_op_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["pc_vector_add"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            ux, uy = int(m.group("ux")), int(m.group("uy"))
            vx, vy = int(m.group("vx")), int(m.group("vy"))
            op = m.group("op")
            if op == r"\vec{u} + \vec{v}":
                ex, ey = ux + vx, uy + vy
            elif op == r"\vec{u} - \vec{v}":
                ex, ey = ux - vx, uy - vy
            else:
                sm = re.match(r"(-?\d+)\\vec\{u\}", op)
                self.assertIsNotNone(sm, f"could not parse op: {op!r}")
                scalar = int(sm.group(1))
                ex, ey = scalar * ux, scalar * uy
            s = self.SOLUTION.search(solution)
            self.assertEqual((int(s.group("x")), int(s.group("y"))), (ex, ey),
                             f"{problem!r} -> {solution!r}")


class ParametricToRectangularTests(TestCase):
    PROBLEM = re.compile(
        r"\$x = (?P<a>-?\d+)t (?P<bsign>[+-]) (?P<b>\d+)\$ and "
        r"\$y = (?P<c>-?\d+)t (?P<dsign>[+-]) (?P<d>\d+)\$"
    )
    SOLUTION = re.compile(r"y = (?P<slope>-?\d*)x(?P<int> [+-] \d+)?")

    def test_elimination_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["pc_parametric_to_rectangular"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            a = int(m.group("a"))
            b = int(m.group("b")) * (1 if m.group("bsign") == "+" else -1)
            c = int(m.group("c"))
            d = int(m.group("d")) * (1 if m.group("dsign") == "+" else -1)
            # t = (x - b)/a ; y = c*t + d = (c/a)x + (d - c*b/a)
            exp_slope = c / a
            exp_int = d - exp_slope * b
            s = self.SOLUTION.search(solution)
            self.assertIsNotNone(s, f"could not parse solution: {solution!r}")
            slope_raw = s.group("slope")
            slope = -1 if slope_raw == "-" else (1 if slope_raw == "" else int(slope_raw))
            int_raw = s.group("int")
            intercept = 0
            if int_raw:
                intercept = int(int_raw.replace(" ", ""))
            self.assertAlmostEqual(slope, exp_slope, places=6,
                                   msg=f"{problem!r} -> {solution!r}")
            self.assertAlmostEqual(intercept, exp_int, places=6,
                                   msg=f"{problem!r} -> {solution!r}")
