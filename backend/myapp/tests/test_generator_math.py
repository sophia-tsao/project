"""Math-correctness tests for the generators we own.

Unlike the contract tests (which only check that a generator produces *some*
well-formed output), these verify the *answer is mathematically correct*: each
test parses the generated problem statement, independently recomputes the
expected answer, and asserts the generator's stated solution matches. Run over
many random samples so the check covers the generator's whole input space, not
a single lucky draw.

This is worth doing precisely because these generators are ours — a regression
in the math is our bug to catch, not the library's.
"""
import math
import random
import re

from django.test import TestCase

from myapp.generators import LOCAL_GENERATORS

SAMPLES = 2000


class VertexFormMathTests(TestCase):
    # y=a(x-h)^2+k  ->  vertex (h, k). Captures optional 'a' (incl. '-'),
    # the (x±h) group, and the trailing +k.
    PROBLEM = re.compile(
        r"y=(?P<a>-?\d*)\((?P<hpart>x(?:[+-]\d+)?)\)\^2(?P<k>[+-]\d+)"
    )
    SOLUTION = re.compile(r"\((?P<vx>-?\d+), (?P<vy>-?\d+)\)")

    def test_vertex_matches_standard_form(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["vertex_form"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")

            a_raw = m.group("a")
            a = -1 if a_raw == "-" else (1 if a_raw == "" else int(a_raw))
            hpart = m.group("hpart")
            # "x-3" -> h=3 ; "x+1" -> h=-1 ; "x" -> h=0
            h = 0 if hpart == "x" else -int(hpart[1:])
            k = int(m.group("k"))

            # Vertex x = -B/2A of the expanded form a*x^2 - 2ah*x + (ah^2+k).
            vx = -(-2 * a * h) / (2 * a)
            vy = a * (vx - h) ** 2 + k

            sol = self.SOLUTION.search(solution)
            self.assertEqual(
                (int(sol.group("vx")), int(sol.group("vy"))),
                (int(vx), int(vy)),
                f"vertex wrong for {problem!r} -> {solution!r}",
            )


class AngleSumMathTests(TestCase):
    PAIR = re.compile(r"\\(sin|cos|tan) [AB] = (\d+)/(\d+)")
    TARGET = re.compile(r"\\(sin|cos)\(A\+B\)")
    FRAC = re.compile(r"(-?\d+)/(-?\d+)")

    @staticmethod
    def _angle(func, num, den):
        ratio = int(num) / int(den)
        return {"sin": math.asin, "cos": math.acos, "tan": math.atan}[func](ratio)

    def test_angle_sum_fraction_matches_trig(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["angle_sum"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            pairs = self.PAIR.findall(problem)
            self.assertEqual(len(pairs), 2, f"could not parse: {problem!r}")
            angle_a = self._angle(*pairs[0])
            angle_b = self._angle(*pairs[1])

            target = self.TARGET.search(problem).group(1)
            expected = (
                math.sin(angle_a + angle_b)
                if target == "sin"
                else math.cos(angle_a + angle_b)
            )

            fr = self.FRAC.search(solution)
            stated = int(fr.group(1)) / int(fr.group(2))
            self.assertAlmostEqual(
                stated, expected, places=9,
                msg=f"angle sum wrong for {problem!r} -> {solution!r}",
            )

    def test_solution_fraction_is_fully_reduced(self):
        random.seed(1)
        gen = LOCAL_GENERATORS["angle_sum"]
        for _ in range(SAMPLES):
            _problem, solution = gen()
            fr = self.FRAC.search(solution)
            num, den = int(fr.group(1)), int(fr.group(2))
            self.assertEqual(
                math.gcd(num, den), 1,
                f"fraction not reduced: {solution!r}",
            )


class ArocMathTests(TestCase):
    PROBLEM = re.compile(
        r"function \$(?P<poly>.+?)\$, .*interval \$(?P<a>-?\d+)\$<=x<=\$(?P<b>-?\d+)\$"
    )
    SOLUTION = re.compile(r"\$(?P<ans>-?[\d.]+)\$")
    # A polynomial term: optional sign, optional magnitude, optional x / x^n.
    TERM = re.compile(r"([+-]?)(\d*)x\^(\d+)|([+-]?)(\d*)x(?!\^)|([+-]?\d+)(?!x)")

    @classmethod
    def _parse_poly(cls, poly):
        terms = []
        for m in cls.TERM.finditer(poly):
            if m.group(3) is not None:  # x^n term
                sign = -1 if m.group(1) == "-" else 1
                mag = int(m.group(2)) if m.group(2) else 1
                terms.append((sign * mag, int(m.group(3))))
            elif m.group(0).endswith("x"):  # linear term
                sign = -1 if m.group(4) == "-" else 1
                mag = int(m.group(5)) if m.group(5) else 1
                terms.append((sign * mag, 1))
            elif m.group(6):  # constant
                terms.append((int(m.group(6)), 0))
        return terms

    @staticmethod
    def _evaluate(terms, x):
        return sum(coeff * (x ** exp) for coeff, exp in terms)

    def test_average_rate_of_change_matches_polynomial(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["aroc_over_interval"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            m = self.PROBLEM.search(problem)
            self.assertIsNotNone(m, f"could not parse: {problem!r}")
            terms = self._parse_poly(m.group("poly"))
            a, b = int(m.group("a")), int(m.group("b"))

            expected = (self._evaluate(terms, a) - self._evaluate(terms, b)) / (a - b)
            stated = float(self.SOLUTION.search(solution).group("ans"))
            self.assertAlmostEqual(
                stated, expected, places=6,
                msg=f"AROC wrong for {problem!r} -> {solution!r}",
            )

    def test_polynomial_display_has_no_glued_terms(self):
        # Regression guard: a zero coefficient used to emit e.g. "3x^40x^3".
        random.seed(2)
        gen = LOCAL_GENERATORS["aroc_over_interval"]
        for _ in range(SAMPLES):
            problem, _solution = gen()
            poly = self.PROBLEM.search(problem).group("poly")
            self.assertNotRegex(
                poly, r"\d+x\^\d{2,}",
                f"suspicious exponent (glued terms?): {poly!r}",
            )
