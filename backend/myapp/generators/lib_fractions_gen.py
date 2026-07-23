"""Solveki-local overrides for broken ``mathgenerator`` fraction/factor generators.

Each generator here is named to *exactly* match a stock ``mathgenerator``
generator so ``_make_problem_for_topic`` (which resolves ``LOCAL_GENERATORS``
before the library) picks up our typeable version instead. The library
versions are unusable in the answer box (which does an exact/``parseFloat``
match) for a mix of reasons:

* ``common_factors`` / ``factors`` return Python list literals like
  ``[1, 2, 4]`` — untypeable bracket notation.
* ``fraction_multiplication`` / ``divide_fractions`` return ``\\frac{a}{b}``
  (often unreduced) — untypeable LaTeX.
* ``greatest_common_divisor`` uses eight- and nine-digit operands that are
  impossible to compute by hand.
* ``dice_sum_probability`` returns an unreduced ``\\frac{3}{36}`` and even
  allows a single die (where a "sum" is meaningless).

Our versions return plain integers, reduced ``a/b`` fractions, or ascending
comma-separated lists, and state the required format/order in the problem.
"""
import random
from fractions import Fraction
from math import gcd

from ._registry import register


def _factors_of(n):
    """Return the sorted list of positive divisors of ``n`` (n >= 1)."""
    divisors = set()
    i = 1
    while i * i <= n:
        if n % i == 0:
            divisors.add(i)
            divisors.add(n // i)
        i += 1
    return sorted(divisors)


def _ascending_list(values):
    """Render ints as an ascending, bracket-free ``'1, 2, 4'`` list."""
    return ", ".join(str(v) for v in sorted(values))


def _frac_str(numerator, denominator):
    """Reduce and render typeably: integer when whole, else ``'p/q'``."""
    fr = Fraction(numerator, denominator)
    if fr.denominator == 1:
        return str(fr.numerator)
    return f"{fr.numerator}/{fr.denominator}"


@register
def common_factors(min_val=2, max_val=100):
    r"""Common Factors of Two Numbers

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | List all common factors of 12 and 18... | 1, 2, 3, 6 |

    Overrides the stock ``common_factors``, which answers with a Python list
    literal like ``[1, 2]``. We return an ascending, comma-separated list with
    no brackets.
    """
    a = random.randint(min_val, max_val)
    b = random.randint(min_val, max_val)
    common = sorted(set(_factors_of(a)) & set(_factors_of(b)))
    problem = (
        f"Find all common factors of {a} and {b}. "
        "List all common factors in ascending order, comma-separated "
        "(e.g. 1, 2, 4)."
    )
    solution = _ascending_list(common)
    return problem, solution


@register
def factors(min_val=2, max_val=100):
    r"""Factors of a Number

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | List all factors of 12... | 1, 2, 3, 4, 6, 12 |

    Overrides the stock ``factors``, which answers with a Python list literal.
    We return an ascending, comma-separated list with no brackets.
    """
    n = random.randint(min_val, max_val)
    problem = (
        f"Find all factors of {n}. "
        "List all factors in ascending order, comma-separated "
        "(e.g. 1, 2, 3, 6)."
    )
    solution = _ascending_list(_factors_of(n))
    return problem, solution


@register
def fraction_multiplication(max_val=10):
    r"""Multiplication of Two Fractions

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | $\frac{3}{10} \cdot \frac{2}{5} =$ | 3/25 |

    Overrides the stock ``fraction_multiplication``, which answers with an
    often-unreduced ``\frac{a}{b}``. We return the reduced product in the
    typeable form ``a/b`` (or an integer).
    """
    a = random.randint(1, max_val)
    b = random.randint(1, max_val)
    c = random.randint(1, max_val)
    d = random.randint(1, max_val)
    problem = (
        f"Calculate $\\frac{{{a}}}{{{b}}} \\cdot \\frac{{{c}}}{{{d}}}$. "
        "Give your answer as a fraction in lowest terms in the form a/b, "
        "or an integer."
    )
    solution = _frac_str(a * c, b * d)
    return problem, solution


@register
def divide_fractions(max_val=10):
    r"""Division of Two Fractions

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | $\frac{3}{10} \div \frac{2}{5} =$ | 3/4 |

    Overrides the stock ``divide_fractions``, which answers with an
    often-unreduced ``\frac{a}{b}``. We return the reduced quotient in the
    typeable form ``a/b`` (or an integer).
    """
    a = random.randint(1, max_val)
    b = random.randint(1, max_val)
    # Numerator of the divisor must be non-zero so division is defined.
    c = random.randint(1, max_val)
    d = random.randint(1, max_val)
    problem = (
        f"Calculate $\\frac{{{a}}}{{{b}}} \\div \\frac{{{c}}}{{{d}}}$. "
        "Give your answer as a fraction in lowest terms in the form a/b, "
        "or an integer."
    )
    # (a/b) / (c/d) = a*d / (b*c)
    solution = _frac_str(a * d, b * c)
    return problem, solution


@register
def greatest_common_divisor(min_val=2, max_val=100, count_choices=(2, 3)):
    r"""Greatest Common Divisor (HCF) of Several Numbers

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Find the greatest common divisor (GCD) of 24, 36. | 12 |

    Overrides the stock ``greatest_common_divisor``, which uses eight- and
    nine-digit operands that can't be worked by hand. We pick a few small,
    review-friendly integers. The answer is a single integer.
    """
    count = random.choice(count_choices)
    numbers = [random.randint(min_val, max_val) for _ in range(count)]
    result = 0
    for value in numbers:
        result = gcd(result, value)
    number_list = ", ".join(str(v) for v in numbers)
    problem = (
        f"Find the greatest common divisor (GCD) of {number_list}. "
        "Give your answer as a single integer."
    )
    solution = str(result)
    return problem, solution


@register
def dice_sum_probability(sides=6):
    r"""Probability of a Given Sum on Two Dice

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | If 2 fair 6-sided dice are rolled, the probability of a sum of 9 is... | 1/9 |

    Overrides the stock ``dice_sum_probability``, which returns an unreduced
    ``\frac{3}{36}`` and even permits a single die. We fix the roll at two dice
    and return the probability as a reduced ``a/b`` fraction.
    """
    target = random.randint(2, 2 * sides)
    # Count ordered outcomes of two dice summing to `target`.
    favorable = sum(
        1
        for x in range(1, sides + 1)
        for y in range(1, sides + 1)
        if x + y == target
    )
    total = sides * sides
    problem = (
        f"If 2 fair {sides}-sided dice are rolled at the same time, "
        f"what is the probability of getting a sum of {target}? "
        "Give your answer as a fraction in lowest terms in the form a/b."
    )
    solution = _frac_str(favorable, total)
    return problem, solution
