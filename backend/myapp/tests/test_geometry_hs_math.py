"""Math-correctness tests for the geometry_hs (Georgia HS geometry) generators.

Each test parses the generated problem statement, independently recomputes the
expected answer, and asserts the generator's stated solution matches. Run over
many random samples so the check covers the whole input space.
"""
import math
import random
import re

from django.test import TestCase

from myapp.generators import geometry_hs  # noqa: F401  (registers generators)
from myapp.generators import LOCAL_GENERATORS

SAMPLES = 2000


class RightTriangleSideTests(TestCase):
    PROBLEM = re.compile(
        r"one acute angle measures \$(?P<theta>\d+)\^\\circ\$\. "
        r"The (?P<given>opposite side|adjacent side|hypotenuse) measures "
        r"\$(?P<len>\d+)\$\. Find the "
        r"(?P<target>opposite side|adjacent side|hypotenuse),"
    )
    SOLUTION = re.compile(r"\$(?P<ans>-?[\d.]+)\$")

    @staticmethod
    def _ratio(name, rad):
        return {
            "opposite side": math.sin(rad),
            "adjacent side": math.cos(rad),
            "hypotenuse": 1.0,
        }[name]

    def test_side_matches_trig(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["geo_right_triangle_side"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            theta = int(m.group("theta"))
            length = int(m.group("len"))
            rad = math.radians(theta)
            expected = round(
                length * self._ratio(m.group("target"), rad)
                / self._ratio(m.group("given"), rad),
                3,
            )
            stated = float(self.SOLUTION.search(solution).group("ans"))
            self.assertAlmostEqual(
                stated, expected, places=3,
                msg=f"wrong for {problem!r} -> {solution!r}",
            )


class RightTrianglePythagTests(TestCase):
    LEGS = re.compile(r"legs of length \$(?P<a>\d+)\$ and \$(?P<b>\d+)\$")
    LEG_HYP = re.compile(
        r"a leg of length \$(?P<a>\d+)\$ and a hypotenuse of length \$(?P<c>\d+)\$"
    )
    SOLUTION = re.compile(r"\$(?P<ans>\d+)\$")

    def test_pythag_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["geo_solve_right_triangle_pythag"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            ans = int(self.SOLUTION.search(solution).group("ans"))
            legs = self.LEGS.search(problem)
            leg_hyp = self.LEG_HYP.search(problem)
            if legs:
                a, b = int(legs.group("a")), int(legs.group("b"))
                expected = math.isqrt(a * a + b * b)
                self.assertEqual(expected * expected, a * a + b * b)
            else:
                self.assertIsNotNone(leg_hyp, f"could not parse: {problem!r}")
                a, c = int(leg_hyp.group("a")), int(leg_hyp.group("c"))
                expected = math.isqrt(c * c - a * a)
                self.assertEqual(expected * expected, c * c - a * a)
            self.assertEqual(ans, expected, f"wrong for {problem!r} -> {solution!r}")


class CircleEquationFromCenterRadiusTests(TestCase):
    PROBLEM = re.compile(
        r"center \$\((?P<h>-?\d+), (?P<k>-?\d+)\)\$ and radius \$(?P<r>\d+)\$"
    )
    # Parse (x - h)^2 + (y - k)^2 = r2 with signs folded in.
    SOLUTION = re.compile(
        r"\(x (?P<xs>[+-]) (?P<xv>\d+)\)\^2 \+ \(y (?P<ys>[+-]) (?P<yv>\d+)\)\^2 "
        r"= (?P<r2>\d+)"
    )

    def test_equation_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["geo_circle_equation_from_center_radius"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            p = self.PROBLEM.search(problem)
            s = self.SOLUTION.search(solution)
            self.assertIsNotNone(p, f"could not parse: {problem!r}")
            self.assertIsNotNone(s, f"could not parse: {solution!r}")
            h, k, r = int(p.group("h")), int(p.group("k")), int(p.group("r"))
            # "(x - v)" means h = v ; "(x + v)" means h = -v.
            sol_h = int(s.group("xv")) if s.group("xs") == "-" else -int(s.group("xv"))
            sol_k = int(s.group("yv")) if s.group("ys") == "-" else -int(s.group("yv"))
            self.assertEqual((sol_h, sol_k), (h, k))
            self.assertEqual(int(s.group("r2")), r * r,
                             f"wrong for {problem!r} -> {solution!r}")


class CircleCenterRadiusFromEquationTests(TestCase):
    PROBLEM = re.compile(
        r"\(x (?P<xs>[+-]) (?P<xv>\d+)\)\^2 \+ \(y (?P<ys>[+-]) (?P<yv>\d+)\)\^2 "
        r"= (?P<r2>\d+)"
    )
    SOLUTION = re.compile(r"center \((?P<h>-?\d+), (?P<k>-?\d+)\), r=(?P<r>\d+)")

    def test_center_radius_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["geo_circle_center_radius_from_equation"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            p = self.PROBLEM.search(problem)
            s = self.SOLUTION.search(solution)
            self.assertIsNotNone(p, f"could not parse: {problem!r}")
            self.assertIsNotNone(s, f"could not parse: {solution!r}")
            h = int(p.group("xv")) if p.group("xs") == "-" else -int(p.group("xv"))
            k = int(p.group("yv")) if p.group("ys") == "-" else -int(p.group("yv"))
            r2 = int(p.group("r2"))
            self.assertEqual((int(s.group("h")), int(s.group("k"))), (h, k))
            self.assertEqual(int(s.group("r")) ** 2, r2,
                             f"wrong for {problem!r} -> {solution!r}")


class TranslatePointTests(TestCase):
    PROBLEM = re.compile(
        r"point \$\((?P<x>-?\d+), (?P<y>-?\d+)\)\$ by the vector "
        r"\$\\langle (?P<a>-?\d+), (?P<b>-?\d+) \\rangle\$"
    )
    SOLUTION = re.compile(r"\((?P<x>-?\d+), (?P<y>-?\d+)\)")

    def test_translate_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["geo_translate_point"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            p = self.PROBLEM.search(problem)
            s = self.SOLUTION.search(solution)
            self.assertIsNotNone(p, f"could not parse: {problem!r}")
            x, y = int(p.group("x")), int(p.group("y"))
            a, b = int(p.group("a")), int(p.group("b"))
            self.assertEqual(
                (int(s.group("x")), int(s.group("y"))), (x + a, y + b),
                f"wrong for {problem!r} -> {solution!r}",
            )


class ReflectPointTests(TestCase):
    PROBLEM = re.compile(
        r"point \$\((?P<x>-?\d+), (?P<y>-?\d+)\)\$ over the "
        r"(?P<line>x-axis|y-axis|line \$y=x\$)"
    )
    SOLUTION = re.compile(r"\((?P<x>-?\d+), (?P<y>-?\d+)\)")

    def test_reflect_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["geo_reflect_point"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            p = self.PROBLEM.search(problem)
            s = self.SOLUTION.search(solution)
            self.assertIsNotNone(p, f"could not parse: {problem!r}")
            x, y = int(p.group("x")), int(p.group("y"))
            line = p.group("line")
            if line == "x-axis":
                expected = (x, -y)
            elif line == "y-axis":
                expected = (-x, y)
            else:
                expected = (y, x)
            self.assertEqual(
                (int(s.group("x")), int(s.group("y"))), expected,
                f"wrong for {problem!r} -> {solution!r}",
            )


class RotatePointTests(TestCase):
    PROBLEM = re.compile(
        r"point \$\((?P<x>-?\d+), (?P<y>-?\d+)\)\$ by \$(?P<a>\d+)\^\\circ\$ "
        r"counterclockwise"
    )
    SOLUTION = re.compile(r"\((?P<x>-?\d+), (?P<y>-?\d+)\)")

    def test_rotate_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["geo_rotate_point"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            p = self.PROBLEM.search(problem)
            s = self.SOLUTION.search(solution)
            self.assertIsNotNone(p, f"could not parse: {problem!r}")
            x, y = int(p.group("x")), int(p.group("y"))
            angle = int(p.group("a"))
            if angle == 90:
                expected = (-y, x)
            elif angle == 180:
                expected = (-x, -y)
            else:
                expected = (y, -x)
            self.assertEqual(
                (int(s.group("x")), int(s.group("y"))), expected,
                f"wrong for {problem!r} -> {solution!r}",
            )


class DilatePointTests(TestCase):
    PROBLEM = re.compile(
        r"point \$\((?P<x>-?\d+), (?P<y>-?\d+)\)\$ from the origin by a scale "
        r"factor of \$(?P<f>[\d/]+)\$"
    )
    SOLUTION = re.compile(r"\((?P<x>-?\d+), (?P<y>-?\d+)\)")

    def test_dilate_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["geo_dilate_point"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            p = self.PROBLEM.search(problem)
            s = self.SOLUTION.search(solution)
            self.assertIsNotNone(p, f"could not parse: {problem!r}")
            x, y = int(p.group("x")), int(p.group("y"))
            f = p.group("f")
            if "/" in f:
                num, den = (int(t) for t in f.split("/"))
            else:
                num, den = int(f), 1
            self.assertEqual(
                (int(s.group("x")), int(s.group("y"))),
                (x * num // den, y * num // den),
                f"wrong for {problem!r} -> {solution!r}",
            )


class InscribedAngleTests(TestCase):
    CENTRAL_GIVEN = re.compile(
        r"central angle measures \$(?P<a>\d+)\^\\circ\$\. Find the measure of "
        r"the inscribed"
    )
    INSCRIBED_GIVEN = re.compile(
        r"inscribed angle measures \$(?P<a>\d+)\^\\circ\$\. Find the measure of "
        r"the central"
    )
    SOLUTION = re.compile(r"\$(?P<a>\d+)\$")

    def test_inscribed_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["geo_inscribed_angle"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            ans = int(self.SOLUTION.search(solution).group("a"))
            central = self.CENTRAL_GIVEN.search(problem)
            inscribed = self.INSCRIBED_GIVEN.search(problem)
            if central:
                self.assertEqual(ans, int(central.group("a")) // 2,
                                 f"wrong for {problem!r} -> {solution!r}")
            else:
                self.assertIsNotNone(inscribed, f"could not parse: {problem!r}")
                self.assertEqual(ans, 2 * int(inscribed.group("a")),
                                 f"wrong for {problem!r} -> {solution!r}")


class ConditionalProbabilityTableTests(TestCase):
    PROBLEM = re.compile(
        r"A&X: (?P<ax>\d+), A&Y: (?P<ay>\d+), B&X: (?P<bx>\d+), B&Y: (?P<by>\d+)\. "
        r"Find \$P\((?P<target>[A-Z]) \\mid (?P<cond>[A-Z])\)\$"
    )
    SOLUTION = re.compile(r"\$(?P<n>\d+)/(?P<d>\d+)\$")

    def test_conditional_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["geo_conditional_probability_table"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            p = self.PROBLEM.search(problem)
            s = self.SOLUTION.search(solution)
            self.assertIsNotNone(p, f"could not parse: {problem!r}")
            counts = {
                ("A", "X"): int(p.group("ax")), ("A", "Y"): int(p.group("ay")),
                ("B", "X"): int(p.group("bx")), ("B", "Y"): int(p.group("by")),
            }
            target, cond = p.group("target"), p.group("cond")
            if cond in ("A", "B"):
                denom = counts[(cond, "X")] + counts[(cond, "Y")]
                numer = counts[(cond, target)]
            else:
                denom = counts[("A", cond)] + counts[("B", cond)]
                numer = counts[(target, cond)]
            g = math.gcd(numer, denom)
            self.assertEqual(
                (int(s.group("n")), int(s.group("d"))),
                (numer // g, denom // g),
                f"wrong for {problem!r} -> {solution!r}",
            )
            self.assertEqual(math.gcd(int(s.group("n")), int(s.group("d"))), 1)


class CompoundProbabilityTests(TestCase):
    PROBLEM = re.compile(
        r"P\(A\) = (?P<a>\d+)/(?P<b>\d+)\$ and \$P\(B\) = (?P<c>\d+)/(?P<d>\d+)\$\. "
        r"Find \$P\(A \\text\{ (?P<conn>and|or) \} B\)\$"
    )
    SOLUTION = re.compile(r"\$(?P<n>\d+)/(?P<d>\d+)\$")

    def test_compound_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["geo_compound_probability"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            p = self.PROBLEM.search(problem)
            s = self.SOLUTION.search(solution)
            self.assertIsNotNone(p, f"could not parse: {problem!r}")
            a, b = int(p.group("a")), int(p.group("b"))
            c, d = int(p.group("c")), int(p.group("d"))
            if p.group("conn") == "and":
                num, den = a * c, b * d
            else:
                num, den = a * d + c * b - a * c, b * d
            g = math.gcd(num, den)
            self.assertEqual(
                (int(s.group("n")), int(s.group("d"))), (num // g, den // g),
                f"wrong for {problem!r} -> {solution!r}",
            )
            self.assertEqual(math.gcd(int(s.group("n")), int(s.group("d"))), 1)


class ExpectedValueTests(TestCase):
    PROBLEM = re.compile(r"distribution: (?P<body>.+?)\. Find the expected value")
    TERM = re.compile(r"P\(X=(?P<v>-?\d+)\)=(?P<n>\d+)/(?P<d>\d+)")
    SOLUTION = re.compile(r"\$(?P<ans>-?[\d.]+)\$")

    def test_ev_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["geo_expected_value"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            body = self.PROBLEM.search(problem)
            self.assertIsNotNone(body, f"could not parse: {problem!r}")
            terms = self.TERM.findall(body.group("body"))
            self.assertGreater(len(terms), 0, f"no terms: {problem!r}")
            ev = round(sum(int(v) * int(n) / int(d) for v, n, d in terms), 3)
            stated = float(self.SOLUTION.search(solution).group("ans"))
            self.assertAlmostEqual(
                stated, ev, places=3,
                msg=f"wrong for {problem!r} -> {solution!r}",
            )
