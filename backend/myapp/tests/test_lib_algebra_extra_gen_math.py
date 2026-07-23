"""Math-correctness tests for the ``expanding`` and ``power_rule_differentiation``
local overrides.

Each test parses the polynomial(s) out of the problem statement, independently
recomputes the expected result, and asserts the generator's solution matches —
over many random samples. Also guards typeability: no LaTeX braces, and the
answer is in strictly descending power order.
"""
import random
import re

from django.test import TestCase

from myapp.generators import lib_algebra_extra_gen  # noqa: F401
from myapp.generators import LOCAL_GENERATORS

SAMPLES = 1000

# One term of a typeable polynomial answer: optional sign, optional coeff,
# 'x', optional '^power'. Constants have no 'x'.
_TERM = re.compile(r"(?P<coeff>-?\d*)x(?:\^(?P<power>\d+))?|(?P<const>-?\d+)")


def _parse_solution(text):
    """Parse a typeable polynomial string into a {power: coeff} dict."""
    terms = {}
    # Normalise ' - '/' + ' joins into signed tokens, then split on whitespace.
    normalized = text.replace(" + ", " +").replace(" - ", " -")
    for token in normalized.split():
        token = token.lstrip("+")  # a leading '+' isn't part of the number
        m = _TERM.fullmatch(token)
        assert m, f"unparseable term {token!r} in {text!r}"
        if m.group("const") is not None:
            terms[0] = terms.get(0, 0) + int(m.group("const"))
            continue
        c = m.group("coeff")
        coeff = 1 if c in ("", "+") else (-1 if c == "-" else int(c))
        power = int(m.group("power")) if m.group("power") else 1
        terms[power] = terms.get(power, 0) + coeff
    return terms


def _assert_typeable_descending(test, solution):
    test.assertNotIn("{", solution)
    test.assertNotIn("}", solution)
    test.assertNotIn("\\", solution)
    powers = [int(p) if p else 1 for p in re.findall(r"x(?:\^(\d+))?", solution)]
    test.assertEqual(powers, sorted(powers, reverse=True),
                     f"terms not in descending order: {solution!r}")


class ExpandingTests(TestCase):
    FACTOR = re.compile(r"\((-?\d*)x([+-]\d+)?\)")

    def test_product_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["expanding"]
        for _ in range(SAMPLES):
            problem, solution = gen()
            factors = self.FACTOR.findall(problem)
            self.assertEqual(len(factors), 2, f"parse fail: {problem!r}")

            def coeffs(lead, const):
                lead = 1 if lead == "" else (-1 if lead == "-" else int(lead))
                const = int(const) if const else 0
                return lead, const

            a, b = coeffs(*factors[0])
            c, d = coeffs(*factors[1])
            expected = {2: a * c, 1: a * d + b * c, 0: b * d}
            expected = {p: v for p, v in expected.items() if v != 0}

            got = _parse_solution(solution)
            got = {p: v for p, v in got.items() if v != 0}
            self.assertEqual(got, expected, f"{problem!r} -> {solution!r}")
            _assert_typeable_descending(self, solution)


class PowerRuleDifferentiationTests(TestCase):
    def test_derivative_matches(self):
        random.seed(0)
        gen = LOCAL_GENERATORS["power_rule_differentiation"]
        term_re = re.compile(r"(\d+)x\^\{(\d+)\}")
        for _ in range(SAMPLES):
            problem, solution = gen()
            shown = problem.split("$")[1]
            src = {}
            for c, p in term_re.findall(shown):
                src[int(p)] = src.get(int(p), 0) + int(c)

            expected = {}
            for p, c in src.items():
                expected[p - 1] = expected.get(p - 1, 0) + c * p
            expected = {p: v for p, v in expected.items() if v != 0}

            got = _parse_solution(solution)
            got = {p: v for p, v in got.items() if v != 0}
            self.assertEqual(got, expected, f"{problem!r} -> {solution!r}")
            _assert_typeable_descending(self, solution)
