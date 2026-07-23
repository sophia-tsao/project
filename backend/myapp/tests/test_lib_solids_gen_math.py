"""Math-correctness tests for the ``lib_solids_gen`` library overrides.

For each override this parses the numeric inputs out of the PROBLEM string,
recomputes the expected answer independently (rounding the same way, to the
nearest thousandth via the shared ``num`` helper), and asserts the generator's
solution matches — over many seeded random samples. Also guards that neither the
problem nor the solution contains a banned LaTeX token or a number with more
than three decimal places.
"""
import math
import random
import re

from django.test import TestCase

# Importing the module runs its @register side effect.
from myapp.generators import lib_solids_gen  # noqa: F401
from myapp.generators import LOCAL_GENERATORS
from myapp.generators._format import num

SAMPLES = 500

# Tokens that must never appear in a typeable problem/solution answer.
_BANNED = [
    r"\frac", r"\sqrt", r"\langle", r"\rangle", r"\geq", r"\leq", r"\neq",
    r"\times", r"\cdot", r"\infty", r"\begin",
]

# Matches any number written with 4+ decimal places (an over-precise leak).
_LONG_DECIMAL = re.compile(r"\d+\.\d{4,}")
# Matches a trailing ``.0`` style number (banned by the typeable rules).
_TRAILING_DOT_ZERO = re.compile(r"\d+\.0\b")


def _assert_typeable(test, problem, solution):
    for tok in _BANNED:
        test.assertNotIn(tok, problem, f"banned {tok!r} in problem: {problem!r}")
        test.assertNotIn(tok, solution, f"banned {tok!r} in solution: {solution!r}")
    for text, label in ((problem, "problem"), (solution, "solution")):
        test.assertIsNone(
            _LONG_DECIMAL.search(text),
            f">3dp number in {label}: {text!r}",
        )
        test.assertIsNone(
            _TRAILING_DOT_ZERO.search(text),
            f"trailing .0 in {label}: {text!r}",
        )


class SurfaceAreaSphereTests(TestCase):
    def test_solution(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["surface_area_sphere"]
        m = re.compile(r"radius \$= (\d+) m\$")
        for _ in range(SAMPLES):
            problem, solution = gen()
            _assert_typeable(self, problem, solution)
            r = int(m.search(problem).group(1))
            expected = num(4 * math.pi * r ** 2)
            self.assertEqual(solution, f"${expected} m^2$", problem)


class VolumeSphereTests(TestCase):
    def test_solution(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["volume_sphere"]
        m = re.compile(r"radius \$= (\d+) m\$")
        for _ in range(SAMPLES):
            problem, solution = gen()
            _assert_typeable(self, problem, solution)
            r = int(m.search(problem).group(1))
            expected = num((4 / 3) * math.pi * r ** 3)
            self.assertEqual(solution, f"${expected} m^3$", problem)


class VolumeHemisphereTests(TestCase):
    def test_solution(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["volume_hemisphere"]
        m = re.compile(r"radius \$= (\d+) m\$")
        for _ in range(SAMPLES):
            problem, solution = gen()
            _assert_typeable(self, problem, solution)
            r = int(m.search(problem).group(1))
            expected = num((2 / 3) * math.pi * r ** 3)
            self.assertEqual(solution, f"${expected} m^3$", problem)


class VolumePyramidTests(TestCase):
    def test_solution(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["volume_pyramid"]
        m = re.compile(r"base area \$= (\d+) m\^2\$ and height \$= (\d+) m\$")
        for _ in range(SAMPLES):
            problem, solution = gen()
            _assert_typeable(self, problem, solution)
            base_area, height = (int(g) for g in m.search(problem).groups())
            expected = num((1 / 3) * base_area * height)
            self.assertEqual(solution, f"${expected} m^3$", problem)


class CurvedSurfaceAreaCylinderTests(TestCase):
    def test_solution(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["curved_surface_area_cylinder"]
        m = re.compile(r"radius \$= (\d+) m\$ and height \$= (\d+) m\$")
        for _ in range(SAMPLES):
            problem, solution = gen()
            _assert_typeable(self, problem, solution)
            r, h = (int(g) for g in m.search(problem).groups())
            expected = num(2 * math.pi * r * h)
            self.assertEqual(solution, f"${expected} m^2$", problem)


class CubeRootTests(TestCase):
    def test_solution(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["cube_root"]
        m = re.compile(r"cube root of \$(\d+)\$")
        for _ in range(SAMPLES):
            problem, solution = gen()
            _assert_typeable(self, problem, solution)
            n = int(m.search(problem).group(1))
            root = round(n ** (1 / 3))
            # The generator only picks perfect cubes: verify that invariant.
            self.assertEqual(root ** 3, n, f"not a perfect cube: {problem!r}")
            self.assertEqual(solution, f"${num(root)}$", problem)


class AreaOfTriangleTests(TestCase):
    def test_solution(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["area_of_triangle"]
        m = re.compile(
            r"side lengths \$= (\d+) m\$, \$= (\d+) m\$, and \$= (\d+) m\$"
        )
        for _ in range(SAMPLES):
            problem, solution = gen()
            _assert_typeable(self, problem, solution)
            a, b, c = (int(g) for g in m.search(problem).groups())
            # Sides must form a strictly valid triangle.
            self.assertTrue(a + b > c and a + c > b and b + c > a, problem)
            s = (a + b + c) / 2
            expected = num(math.sqrt(s * (s - a) * (s - b) * (s - c)))
            self.assertEqual(solution, f"${expected} m^2$", problem)


class PythagoreanTheoremTests(TestCase):
    def test_solution(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["pythagorean_theorem"]
        m = re.compile(r"lengths \$= (\d+)\$ and \$= (\d+)\$")
        for _ in range(SAMPLES):
            problem, solution = gen()
            _assert_typeable(self, problem, solution)
            a, b = (int(g) for g in m.search(problem).groups())
            expected = num(math.sqrt(a ** 2 + b ** 2))
            self.assertEqual(solution, f"${expected}$", problem)
