"""Solveki-local algebra generators."""
import random

from ._registry import register
from ._format import num as _num


def _format_polynomial(terms):
    """Render ``(coefficient, exponent)`` pairs as a polynomial string.

    Zero-coefficient terms are dropped, signs are joined with the right
    operator, and unit coefficients omit the leading ``1`` (e.g. ``x^2``,
    ``-x``). ``terms`` should be ordered from the highest exponent down.
    """
    pieces = []
    for coeff, exp in terms:
        if coeff == 0:
            continue
        sign = "-" if coeff < 0 else "+"
        magnitude = abs(coeff)
        if exp == 0:
            body = str(magnitude)
        else:
            var = "x" if exp == 1 else f"x^{exp}"
            # Omit the coefficient entirely when it's 1 (or -1): "x", not "1x".
            body = var if magnitude == 1 else f"{magnitude}{var}"
        pieces.append((sign, body))

    if not pieces:
        return "0"

    first_sign, first_body = pieces[0]
    result = (first_body if first_sign == "+" else f"-{first_body}")
    for sign, body in pieces[1:]:
        result += f"{sign}{body}"
    return result


@register
def vertex_form(min_val=-10, max_val=10, min_a=-5, max_a=5):
    r"""Vertex of a Quadratic in Vertex Form

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Find the coordinates of the vertex of $y=2(x-3)^2+4$ | $(3, 4)$ |
    """
    a = random.choice([i for i in range(min_a, max_a + 1) if i != 0])
    h = random.randint(min_val, max_val)
    k = random.randint(min_val, max_val)

    h_str = f"x{'+' if -h >= 0 else '-'}{abs(h)}" if h != 0 else "x"
    a_str = "" if a == 1 else ("-" if a == -1 else str(a))

    problem = f"Find the coordinates of the vertex of $y={a_str}({h_str})^2{'+' if k >= 0 else '-'}{abs(k)}$"
    solution = f"$({h}, {k})$"
    return problem, solution


@register
def aroc_over_interval(max_degree=5, max_coefficient=10, min_coefficient=-10):
    r"""Average Rate of Change over an Interval

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Given the function $2x^2+3$, find the average rate of change over the interval $1<=x<=4$ | $10.0$ |
    """
    degree = random.randint(1, max_degree)
    x_value1 = random.randint(-10, 5)
    x_value2 = random.randint(x_value1 + 1, 10)
    y_value1 = 0
    y_value2 = 0
    # Collect (coefficient, exponent) pairs, then render so signs, unit
    # coefficients, and zero terms are formatted correctly.
    terms = []
    for i in range(degree, 0, -1):
        coeff = random.randint(min_coefficient, max_coefficient)
        terms.append((coeff, i))
        y_value1 += (x_value1 ** i) * coeff
        y_value2 += (x_value2 ** i) * coeff
    constant = random.choice(
        [c for c in range(min_coefficient, max_coefficient + 1) if c != 0]
    )
    terms.append((constant, 0))
    y_value1 += constant
    y_value2 += constant

    function = _format_polynomial(terms)
    ans = (y_value1 - y_value2) / (x_value1 - x_value2)
    problem = (
        f"Given the function ${function}$, find the average rate of change "
        f"over the interval ${x_value1}$<=x<=${x_value2}$. "
        f"Round your answer to the nearest thousandth."
    )
    solution = f"${_num(ans)}$"
    return problem, solution
