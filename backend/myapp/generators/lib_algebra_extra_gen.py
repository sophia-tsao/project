"""Solveki-local overrides for two more broken ``mathgenerator`` generators.

Both are named to *exactly* match a stock ``mathgenerator`` generator so
``_make_problem_for_topic`` (which resolves ``LOCAL_GENERATORS`` before the
library) picks up our version. They were caught by the served-problem quality
contract test in ``test_generators.py`` rather than by the initial sweep,
because the stock versions fail on random draws the sampling missed:

* ``expanding`` (Expanding Factored Binomial) raises ``IndexError`` on some
  inputs — a 500 for the student — and even when it doesn't, it can emit a
  malformed product like ``-14x^2x+3``.
* ``power_rule_differentiation`` returns the derivative with LaTeX braces
  (``90x^{9} + 30x^{2}``) that can't be typed into the answer box, lists terms
  in the problem's arbitrary order, and shows ugly ``1x^{5}`` coefficients.

Each generator takes no required arguments, is ``@register``-ed, and returns a
``(problem, solution)`` pair whose solution is strictly keyboard-typeable
(integers and ``a^b`` powers with a plain ASCII caret).
"""
import random

from ._registry import register


def _term(coeff, power):
    """Render one polynomial term typeably (ASCII caret, drop unit coeff/^1).

    ``coeff`` may be negative; the caller joins terms with explicit signs, so
    this renders the magnitude's variable part and keeps the sign on the
    coefficient (e.g. ``-3x^2``). A zero coefficient yields ``"0"``.
    """
    if coeff == 0:
        return "0"
    if power == 0:
        return str(coeff)
    var = "x" if power == 1 else f"x^{power}"
    if coeff == 1:
        return var
    if coeff == -1:
        return f"-{var}"
    return f"{coeff}{var}"


def _poly_str(terms):
    """Render ``{power: coeff}`` as a descending-power polynomial string.

    Zero coefficients are dropped. The leading term keeps its own sign; each
    subsequent term is joined with `` + `` or `` - `` so the result reads like
    ``4x^3 - 2x^2 + x - 5``. Returns ``"0"`` if every coefficient is zero.
    """
    powers = [p for p in sorted(terms, reverse=True) if terms[p] != 0]
    if not powers:
        return "0"
    out = _term(terms[powers[0]], powers[0])
    for p in powers[1:]:
        coeff = terms[p]
        op = " + " if coeff > 0 else " - "
        out += op + _term(abs(coeff), p)
    return out


@register
def expanding(max_coeff=9):
    r"""Expanding Factored Binomial

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Expand $(2x-1)(3x+4)$. | 6x^2 + 5x - 4 |

    ``(ax+b)(cx+d) = ac x^2 + (ad+bc) x + bd``. Overrides the stock
    ``expanding``, which raises ``IndexError`` on some draws and can emit a
    malformed product. The answer is a typeable quadratic in descending order.
    """
    nonzero = [n for n in range(-max_coeff, max_coeff + 1) if n != 0]
    a = random.choice(nonzero)
    c = random.choice(nonzero)
    b = random.randint(-max_coeff, max_coeff)
    d = random.randint(-max_coeff, max_coeff)

    def _factor(lead, const):
        # Render one factor like (2x-1); lead is nonzero.
        lead_str = "x" if lead == 1 else ("-x" if lead == -1 else f"{lead}x")
        if const == 0:
            return f"({lead_str})"
        return f"({lead_str}{'+' if const > 0 else '-'}{abs(const)})"

    coeffs = {2: a * c, 1: a * d + b * c, 0: b * d}
    problem = (
        f"Expand ${_factor(a, b)}{_factor(c, d)}$. "
        "Write your answer with terms in descending order of power, "
        "e.g. 6x^2 + 5x - 4."
    )
    return problem, _poly_str(coeffs)


@register
def power_rule_differentiation(min_power=1, max_power=8):
    r"""Power Rule Differentiation

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Differentiate $3x^{5}+2x^{2}$. | 15x^4 + 4x |

    ``d/dx (c x^n) = c*n x^(n-1)``. Overrides the stock generator, which
    returned the derivative with untypeable LaTeX braces. Here the answer is a
    typeable polynomial in descending power order with an ASCII caret.
    """
    powers = random.sample(range(min_power, max_power + 1),
                           random.randint(2, 4))
    coeffs = {p: random.randint(1, 9) for p in powers}
    shown = " + ".join(f"{coeffs[p]}x^{{{p}}}" for p in sorted(powers, reverse=True))

    # Derivative: c x^n -> (c*n) x^(n-1). A power-1 term becomes a constant.
    deriv = {}
    for p, c in coeffs.items():
        deriv[p - 1] = deriv.get(p - 1, 0) + c * p

    problem = (
        f"Differentiate ${shown}$ with respect to $x$. "
        "Write your answer with terms in descending order of power, "
        "e.g. 15x^4 + 4x."
    )
    return problem, _poly_str(deriv)
