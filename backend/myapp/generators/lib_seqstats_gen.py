"""Solveki-local overrides for broken ``mathgenerator`` sequence / integral /
statistics generators (assignment group G5).

Each generator here is named to *exactly* match a stock ``mathgenerator``
generator so ``_make_problem_for_topic`` (which resolves ``LOCAL_GENERATORS``
before the library) picks up our typeable version instead. The library
versions are unusable in the answer box (which does an exact/``parseFloat``
match) for a mix of reasons:

* ``mean_median`` has typos in its problem ("arithmatic", "mdian") and answers
  with a full English sentence rather than a typeable value.
* ``data_summary`` emits raw 16-digit floats and never says whether the
  statistics are the population or sample versions.
* ``arithmetic_progression_sum`` answers with a trailing ``.0`` (``78267.0``).
* ``geometric_progression`` returns a verbose multi-part sentence.
* ``definite_integral`` emits long truncated decimals like ``89.6667``.
* ``power_rule_integration`` returns untypeable ``\\frac{3}{8}x^{9}+...+C``.
* ``confidence_interval`` returns a tuple of 16-digit floats, sometimes with
  the endpoints reversed (high, low).
* ``quadratic_equation`` answers with brace set notation ``{-0.67, -9.83}`` and
  gives no instruction about format or ordering.

Our versions return plain integers, reduced ``a/b`` fractions, ordered pairs, or
comma-separated lists, and state the required format/order in the problem.
"""
import math
import random
from fractions import Fraction

from ._registry import register
from ._format import num as _num, frac_from as _frac_from


def _median(values):
    """Median of a list; mean of the two middle values when the count is even."""
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


@register
def mean_median(min_val=1, max_val=100):
    r"""Mean and Median of a Series

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Given the series 9, 16, 18, 33, 58. Find the mean and median. | 26.8, 18 |

    Overrides the stock ``mean_median``, which misspells "arithmetic" and
    "median" and answers with a full sentence. We fix the typos and return two
    typeable numbers.
    """
    n = random.choice([5, 6, 7, 8, 9, 10])
    data = [random.randint(min_val, max_val) for _ in range(n)]
    mean = sum(data) / n
    median = _median(data)
    problem = (
        f"Given the series of numbers: {', '.join(str(v) for v in data)}. "
        "Find the arithmetic mean and the median of the series. "
        "Give your answer as mean, median, both rounded to the nearest "
        "thousandth."
    )
    solution = f"{_num(mean)}, {_num(median)}"
    return problem, solution


@register
def data_summary(min_val=1, max_val=50):
    r"""Mean, Standard Deviation and Variance of a Data Set

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Find the population mean, standard deviation and variance of ... | 25, 12.452, 155.067 |

    Overrides the stock ``data_summary``, which emits 16-digit floats and never
    states whether the statistics are the population or sample versions. We use
    the population versions (divide by N), state so explicitly, and round every
    number to three decimals.
    """
    n = random.choice([10, 12, 15])
    data = [random.randint(min_val, max_val) for _ in range(n)]
    mean = sum(data) / n
    variance = sum((x - mean) ** 2 for x in data) / n
    std_dev = math.sqrt(variance)
    problem = (
        f"For the data set: {', '.join(str(v) for v in data)}. "
        "Find the population mean, the population standard deviation, and the "
        "population variance (the standard deviation and variance divide by N, "
        "the number of values). Give your answer as mean, standard deviation, "
        "variance, each rounded to the nearest thousandth."
    )
    solution = f"{_num(mean)}, {_num(std_dev)}, {_num(variance)}"
    return problem, solution


@register
def arithmetic_progression_sum(min_a=-50, max_a=50, min_d=-12, max_d=12):
    r"""Sum of an Arithmetic Progression

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Sum of the first 12 terms with first term 45, common difference -66. | -3816 |

    Overrides the stock ``arithmetic_progression_sum``, whose answer carries a
    trailing ``.0``. The sum of an integer AP is always an integer; we return it
    as a plain integer.
    """
    a = random.randint(min_a, max_a)
    d = random.randint(min_d, max_d)
    n = random.randint(5, 60)
    # S_n = n/2 * (2a + (n - 1) d); always integral for integer a, d, n.
    total = n * (2 * a + (n - 1) * d) // 2
    problem = (
        f"Find the sum of the first {n} terms of an arithmetic progression "
        f"with first term {a} and common difference {d}. "
        "Give your answer as a single integer."
    )
    solution = _num(total)
    return problem, solution


@register
def geometric_progression(min_a=1, max_a=9, min_r=2, max_r=5):
    r"""Nth Term of a Geometric Progression

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | GP with first term 3 and common ratio 2. Find the 5th term. | 48 |

    Overrides the stock ``geometric_progression``, which returns a verbose
    multi-part sentence. We ask for one thing -- the nth term, a * r^(n-1) --
    and answer with a single integer.
    """
    a = random.randint(min_a, max_a)
    r = random.randint(min_r, max_r)
    n = random.randint(3, 7)
    term = a * r ** (n - 1)
    problem = (
        f"A geometric progression has first term a = {a} and common ratio "
        f"r = {r}. Find the {n}th term (a * r^(n-1)). "
        "Give your answer as a single integer."
    )
    solution = _num(term)
    return problem, solution


@register
def definite_integral(min_coef=1, max_coef=20):
    r"""Definite Integral of a Quadratic

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Integral of 17x^2 + 72x + 97 from x = 0 to x = 1. | 416/3 |

    Overrides the stock ``definite_integral``, which emits truncated decimals
    like ``89.6667``. The exact value is rational, so we return it as a reduced
    ``a/b`` fraction (or an integer).
    """
    p = random.randint(min_coef, max_coef)
    q = random.randint(min_coef, max_coef)
    s = random.randint(min_coef, max_coef)
    a = random.randint(-3, 2)
    b = random.randint(a + 1, 4)

    def antideriv(x):
        # Antiderivative of p x^2 + q x + s is p/3 x^3 + q/2 x^2 + s x.
        x = Fraction(x)
        return Fraction(p, 3) * x ** 3 + Fraction(q, 2) * x ** 2 + s * x

    value = antideriv(b) - antideriv(a)
    problem = (
        f"Evaluate the definite integral of {p}x^2 + {q}x + {s} "
        f"from x = {a} to x = {b}. "
        "Give your answer as a fraction in lowest terms in the form a/b, "
        "or an integer."
    )
    solution = _frac_from(value)
    return problem, solution


@register
def power_rule_integration(max_terms=3, max_coef=9, max_exp=5):
    r"""Indefinite Integral of a Polynomial (Power Rule)

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Antiderivative of 3x. | 3/2x^2 + C |

    Overrides the stock ``power_rule_integration``, which returns untypeable
    ``\frac{a}{b}x^{n}+...+C``. We integrate a short polynomial and write the
    antiderivative in typeable ASCII: descending powers, coefficients as
    integers or reduced ``a/b`` fractions, powers as ``x^n``, ending in ``+ C``.
    """
    count = random.randint(1, max_terms)
    exps = random.sample(range(1, max_exp + 1), count)
    # {exponent: coefficient} of the integrand.
    integrand = {e: random.randint(1, max_coef) for e in exps}

    def render_integrand_term(exp, coef):
        return f"{coef}x" if exp == 1 else f"{coef}x^{exp}"

    integrand_str = " + ".join(
        render_integrand_term(e, integrand[e]) for e in sorted(integrand, reverse=True)
    )

    # Integrate: c x^e -> c/(e+1) x^(e+1). New exponents are all >= 2.
    antideriv = {e + 1: Fraction(c, e + 1) for e, c in integrand.items()}
    terms = [
        f"{_frac_from(coef)}x^{ne}"
        for ne, coef in sorted(antideriv.items(), reverse=True)
    ]
    solution = " + ".join(terms) + " + C"

    problem = (
        f"Find the indefinite integral (antiderivative) of {integrand_str}. "
        "Write the terms in descending powers of x, with coefficients as "
        "integers or reduced fractions a/b and powers written as x^n, ending "
        "with + C (for example, 1/2x^2 + 3x + C)."
    )
    return problem, solution


# Confidence level -> two-sided normal critical value.
_Z_CRITICAL = {80: 1.282, 90: 1.645, 95: 1.96, 99: 2.576}


@register
def confidence_interval():
    r"""Confidence Interval for a Mean

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | mean 50, std 8, n = 25, z = 1.96. | (46.864, 53.136) |

    Overrides the stock ``confidence_interval``, which returns a tuple of
    16-digit floats sometimes in reversed (high, low) order. We compute
    mean +/- z * s/sqrt(n), return the endpoints low < high rounded to three
    decimals, and state the format.
    """
    mean = random.randint(20, 100)
    s = random.randint(2, 30)
    n = random.randint(5, 200)
    confidence = random.choice(sorted(_Z_CRITICAL))
    z = _Z_CRITICAL[confidence]

    margin = z * s / math.sqrt(n)
    low = mean - margin
    high = mean + margin
    problem = (
        f"A sample has mean {mean}, standard deviation {s}, and size n = {n}. "
        f"Using the critical value z = {_num(z)} (a {confidence}% confidence "
        "level), find the confidence interval mean +/- z * s / sqrt(n). "
        "Format your answer as (low, high) rounded to the nearest thousandth."
    )
    solution = f"({_num(low)}, {_num(high)})"
    return problem, solution


@register
def quadratic_equation(max_num=6, max_den=3):
    r"""Zeros of a Quadratic Equation

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Solve 2x^2 - x - 1 = 0. | -1/2, 1 |

    Overrides the stock ``quadratic_equation``, which answers with brace set
    notation and no instruction. We build the quadratic from two rational roots
    so the zeros are always rational, and return them as a comma-separated list,
    smaller first, each an integer or reduced ``a/b`` fraction.
    """
    def make_root():
        d = random.randint(1, max_den)
        num = random.choice([v for v in range(-max_num, max_num + 1) if v != 0])
        return Fraction(num, d)

    while True:
        r1 = make_root()
        r2 = make_root()
        # Clear denominators to integer coefficients: a x^2 + b x + c.
        a = r1.denominator * r2.denominator
        b = -(a * (r1 + r2))
        c = a * r1 * r2
        b = int(b)
        c = int(c)
        # Keep a clean, fully three-term equation (nonzero b and c) with two
        # distinct roots.
        if r1 != r2 and b != 0 and c != 0:
            break

    lo, hi = sorted((r1, r2))

    b_sign, b_abs = ("+", b) if b >= 0 else ("-", -b)
    c_sign, c_abs = ("+", c) if c >= 0 else ("-", -c)
    equation = f"{a}x^2 {b_sign} {b_abs}x {c_sign} {c_abs} = 0"
    problem = (
        f"Solve the quadratic equation {equation}. "
        "Give the two solutions as a comma-separated list, smaller first, "
        "each an integer or reduced fraction a/b (for example, -1/2, 1)."
    )
    solution = f"{_frac_from(lo)}, {_frac_from(hi)}"
    return problem, solution
