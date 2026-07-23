"""Solveki-local overrides for broken ``mathgenerator`` powers/algebra generators.

Every generator here is named to *exactly* match a stock ``mathgenerator``
generator so ``_make_problem_for_topic`` (which resolves ``LOCAL_GENERATORS``
before the library) picks up our version. The stock versions in this group are
unusable in an exact-match answer box for various reasons:

* ``system_of_equations`` gives no answer-format instruction.
* ``combine_like_terms`` lists terms in ascending order with ugly ``1x^{5}``.
* ``quotient_of_power_same_base`` leaks LaTeX braces into visible text and can
  emit tiny scientific-notation floats like ``4.14e-08``.
* ``quotient_of_power_same_power`` emits long non-terminating decimals.
* ``product_of_scientific_notations`` returns ``2.17 \times 10^{97}`` — untypeable.

Each generator takes no required arguments, is ``@register``-ed, and returns a
``(problem, solution)`` pair whose *solution* is strictly keyboard-typeable
(integers, ``a/b`` fractions, ``a^b`` powers, ``m*10^e`` sci-notation).
"""
import random
from fractions import Fraction

from ._registry import register
from ._format import num


def _signed_term(coeff, var):
    """A signed term like ``+3y`` / ``-3y`` (coefficient always shown)."""
    return f"{'+' if coeff >= 0 else '-'}{abs(coeff)}{var}"


@register
def system_of_equations(max_coeff=6, min_sol=-8, max_sol=8):
    r"""Solve a System of Equations in R^2

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Given $2x+3y=13$ and $1x-1y=1$, solve for x and y. | x=3, y=-2 |

    Overrides the stock ``system_of_equations``, which states no answer format.
    Coefficients are chosen with a nonzero determinant so the integer solution
    ``(x, y)`` is unique.
    """
    nonzero = [n for n in range(-max_coeff, max_coeff + 1) if n != 0]
    while True:
        a, b, c, d = (random.choice(nonzero) for _ in range(4))
        if a * d - b * c != 0:
            break
    x = random.randint(min_sol, max_sol)
    y = random.randint(min_sol, max_sol)
    e = a * x + b * y
    f = c * x + d * y
    eq1 = f"{a}x{_signed_term(b, 'y')}={e}"
    eq2 = f"{c}x{_signed_term(d, 'y')}={f}"
    problem = (
        f"Given ${eq1}$ and ${eq2}$, solve for x and y. "
        f"Format your answer as x=.., y=.. (e.g. x=3, y=-2)."
    )
    solution = f"x={x}, y={y}"
    return problem, solution


def _combine_term(coeff, power):
    """Render one combined term typeably (ASCII caret, drop unit coeff/^1)."""
    if power == 0:
        return str(coeff)
    var = "x" if power == 1 else f"x^{power}"
    return var if coeff == 1 else f"{coeff}{var}"


@register
def combine_like_terms(min_power=1, max_power=6):
    r"""Combine Like Terms

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Combine like terms: $2x^{3}+5x^{2}+2x^{3}$ | 4x^3 + 5x^2 |

    Overrides the stock ``combine_like_terms``, which lists terms in ascending
    power order with ``1x^{5}``-style coefficients. Here the answer is in
    descending power order, unit coefficients and ``^1`` are dropped, and the
    caret is plain ASCII so the answer is typeable.
    """
    powers = random.sample(range(min_power, max_power + 1),
                           random.randint(2, 4))
    addends = []          # (coeff, power) shown, possibly repeated per power
    combined = {}         # power -> summed coeff
    for p in powers:
        for _ in range(random.randint(1, 2)):
            c = random.randint(1, 5)
            addends.append((c, p))
            combined[p] = combined.get(p, 0) + c

    random.shuffle(addends)
    shown = " + ".join(f"{c}x^{{{p}}}" for c, p in addends)
    problem = (
        f"Combine like terms: ${shown}$. "
        "Write your answer with terms in descending order of power, "
        "e.g. 4x^3 + 2x^2 + x + 5."
    )
    solution = " + ".join(
        _combine_term(combined[p], p) for p in sorted(combined, reverse=True)
    )
    return problem, solution


@register
def power_of_powers(min_base=2, max_base=20, min_exp=2, max_exp=9):
    r"""Power of Powers

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Simplify $(9^{7})^{9}$ | 9^63 |

    ``(a^m)^n = a^(m*n)``. Answer uses an ASCII caret with no braces.
    """
    a = random.randint(min_base, max_base)
    m = random.randint(min_exp, max_exp)
    n = random.randint(min_exp, max_exp)
    problem = (
        f"Simplify $({a}^{{{m}}})^{{{n}}}$. Write your answer in the form a^b."
    )
    solution = f"{a}^{m * n}"
    return problem, solution


@register
def quotient_of_power_same_base(min_base=2, max_base=20, min_exp=2, max_exp=9):
    r"""Quotient of Powers with the Same Base

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Simplify the quotient $9^{10} / 9^{2}$ | 9^8 |

    ``a^m / a^n = a^(m-n)``. Overrides the stock generator, which leaked LaTeX
    braces into the visible problem text and could emit tiny sci-notation floats
    like ``4.14e-08`` for negative exponents. Here ``m > n`` always, so the
    result exponent is a positive integer and the answer stays in clean ``a^b``
    form.
    """
    a = random.randint(min_base, max_base)
    n = random.randint(min_exp, max_exp)
    m = n + random.randint(2, max_exp)  # m > n, so m - n >= 2
    problem = (
        f"Simplify the quotient ${a}^{{{m}}} / {a}^{{{n}}}$. "
        "Write your answer in the form a^b."
    )
    solution = f"{a}^{m - n}"
    return problem, solution


@register
def quotient_of_power_same_power(min_base=2, max_base=12, min_exp=2, max_exp=6):
    r"""Quotient of Powers with the Same Power

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Simplify the quotient $9^{2} / 37^{2}$ | (9/37)^2 |

    ``a^n / b^n = (a/b)^n``. Overrides the stock generator, which emitted long
    non-terminating decimals (e.g. ``0.2432...^2``). Here the base is kept as a
    reduced fraction; when it reduces to a whole number the answer is ``k^n``.
    """
    while True:
        a = random.randint(min_base, max_base)
        b = random.randint(min_base, max_base)
        if a != b:
            break
    n = random.randint(min_exp, max_exp)
    base = Fraction(a, b)
    if base.denominator == 1:
        answer = f"{base.numerator}^{n}"
    else:
        answer = f"({base.numerator}/{base.denominator})^{n}"
    problem = (
        f"Simplify the quotient ${a}^{{{n}}} / {b}^{{{n}}}$. "
        "Write your answer as (a/b)^n with a/b reduced, "
        "or as k^n if the base is a whole number."
    )
    return problem, answer


@register
def product_of_scientific_notations(min_exp=-9, max_exp=9):
    r"""Product of Scientific Notations

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Compute the product (2.17*10^95)(1.57*10^-70). | 3.407*10^25 |

    ``(a*10^p)(b*10^q) = c*10^r``. Overrides the stock generator, which returned
    an untypeable ``2.17 \times 10^{97}``. The result mantissa is normalised to
    ``[1, 10)`` and rendered via ``num`` (3dp, no trailing ``.0``), and the
    answer uses ASCII ``m*10^e`` form (never ``e-11`` floats).
    """
    a = Fraction(random.randint(100, 999), 100)  # 2dp mantissa in [1.00, 9.99]
    b = Fraction(random.randint(100, 999), 100)
    p = random.randint(min_exp, max_exp)
    q = random.randint(min_exp, max_exp)

    mantissa = a * b            # in [1, ~100)
    exponent = p + q
    if mantissa >= 10:          # normalise to [1, 10)
        mantissa /= 10
        exponent += 1

    problem = (
        f"Compute the product ({num(a)}*10^{p})({num(b)}*10^{q}). "
        "Format your answer as m*10^e, e.g. 5.0*10^4 -> write 5*10^4."
    )
    solution = f"{num(mantissa)}*10^{exponent}"
    return problem, solution
