"""Solveki-local generators for Georgia Advanced Algebra: Concepts & Connections.

These fill computable gaps in the stock ``mathgenerator`` catalogue for the
"Advanced Algebra: Concepts & Connections" course. Every generator in this
module is named with an ``alg2_`` prefix, takes no required arguments, and
returns a ``(problem, solution)`` pair of LaTeX strings.
"""
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
            body = var if magnitude == 1 else f"{magnitude}{var}"
        pieces.append((sign, body))

    if not pieces:
        return "0"

    first_sign, first_body = pieces[0]
    result = first_body if first_sign == "+" else f"-{first_body}"
    for sign, body in pieces[1:]:
        result += f"{sign}{body}"
    return result


def _coeffs_to_terms(coeffs):
    """``[a, b, c]`` (highest degree first) -> ``[(a, 2), (b, 1), (c, 0)]``."""
    degree = len(coeffs) - 1
    return [(c, degree - i) for i, c in enumerate(coeffs)]


def _eval_coeffs(coeffs, x):
    """Evaluate a polynomial given as highest-degree-first coefficients."""
    degree = len(coeffs) - 1
    return sum(c * (x ** (degree - i)) for i, c in enumerate(coeffs))


def _random_poly(min_deg, max_deg):
    """Return highest-first coefficients with a nonzero leading coefficient."""
    degree = random.randint(min_deg, max_deg)
    coeffs = [random.choice([c for c in range(-6, 7) if c != 0])]
    coeffs += [random.randint(-6, 6) for _ in range(degree - 1)]
    coeffs.append(random.choice([c for c in range(-6, 7) if c != 0]))
    return coeffs


def _synthetic_division(coeffs, r):
    """Divide (highest-first) ``coeffs`` by ``(x - r)``.

    Returns ``(quotient_coeffs, remainder)``.
    """
    out = [coeffs[0]]
    for c in coeffs[1:]:
        out.append(c + out[-1] * r)
    return out[:-1], out[-1]


def _divisor_str(r):
    """``(x - r)`` inner text: r=2 -> 'x-2', r=-3 -> 'x+3'."""
    return f"x-{r}" if r > 0 else f"x+{-r}"


def _clean_num(value):
    """Format a number to at most 3 decimal places, trimming trailing zeros."""
    return _num(value)


def _complex_str(a, b):
    """Format ``a + b i`` (b assumed nonzero) as e.g. '3+2i', '1-i', '-4+i'."""
    connector = "+" if b > 0 else "-"
    mag = "i" if abs(b) == 1 else f"{abs(b)}i"
    return f"{a}{connector}{mag}"


def _complex_result_str(p, q):
    """Normalized complex result; p and q are assumed both nonzero here."""
    connector = "+" if q > 0 else "-"
    mag = "i" if abs(q) == 1 else f"{abs(q)}i"
    return f"{p}{connector}{mag}"


def _signed(coeff, var):
    """A trailing signed term, e.g. coeff=-4 var='y' -> '-4y'."""
    return f"{'+' if coeff >= 0 else '-'}{abs(coeff)}{var}"


@register
def alg2_evaluate_polynomial(min_degree=2, max_degree=3, min_x=-5, max_x=5):
    r"""Evaluate a Polynomial at a Value

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Evaluate $p(x)=2x^2+3x-1$ at $x=4$ | $43$ |
    """
    coeffs = _random_poly(min_degree, max_degree)
    x = random.randint(min_x, max_x)
    value = _eval_coeffs(coeffs, x)
    poly = _format_polynomial(_coeffs_to_terms(coeffs))
    problem = f"Evaluate $p(x)={poly}$ at $x={x}$"
    solution = f"${value}$"
    return problem, solution


@register
def alg2_polynomial_division(min_degree=2, max_degree=3, max_root=5):
    r"""Polynomial Division by a Linear Factor

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Divide $p(x)=x^2+5x+6$ by $(x-2)$ | quotient $x+7$, remainder $20$ |
    """
    coeffs = _random_poly(min_degree, max_degree)
    r = random.choice([n for n in range(-max_root, max_root + 1) if n != 0])
    quotient, remainder = _synthetic_division(coeffs, r)
    poly = _format_polynomial(_coeffs_to_terms(coeffs))
    q_str = _format_polynomial(_coeffs_to_terms(quotient))
    problem = (
        f"Divide $p(x)={poly}$ by $({_divisor_str(r)})$. "
        f"Format your answer as 'quotient ..., remainder ...'."
    )
    solution = f"quotient ${q_str}$, remainder ${remainder}$"
    return problem, solution


@register
def alg2_remainder_theorem(min_degree=2, max_degree=3, max_root=5):
    r"""Remainder Theorem

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Find the remainder when $p(x)=x^2+5x+6$ is divided by $(x-2)$ | $20$ |
    """
    coeffs = _random_poly(min_degree, max_degree)
    r = random.choice([n for n in range(-max_root, max_root + 1) if n != 0])
    poly = _format_polynomial(_coeffs_to_terms(coeffs))
    remainder = _eval_coeffs(coeffs, r)
    problem = (
        f"Find the remainder when $p(x)={poly}$ is divided by $({_divisor_str(r)})$"
    )
    solution = f"${remainder}$"
    return problem, solution


@register
def alg2_build_polynomial_from_roots(min_root=-4, max_root=4):
    r"""Build a Polynomial from Its Roots

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Find a monic polynomial in standard form with roots $2$, $-3$, and $1$ | $x^3-7x+6$ |
    """
    count = random.choice([2, 3])
    roots = [random.randint(min_root, max_root) for _ in range(count)]

    coeffs = [1]  # start with the polynomial "1"
    for root in roots:
        shifted = coeffs + [0]
        scaled = [0] + [c * (-root) for c in coeffs]
        coeffs = [s + t for s, t in zip(shifted, scaled)]

    poly = _format_polynomial(_coeffs_to_terms(coeffs))
    if count == 2:
        roots_text = f"${roots[0]}$ and ${roots[1]}$"
    else:
        roots_text = f"${roots[0]}$, ${roots[1]}$, and ${roots[2]}$"
    problem = f"Find a monic polynomial in standard form with roots {roots_text}"
    solution = f"${poly}$"
    return problem, solution


@register
def alg2_add_complex(min_val=-9, max_val=9):
    r"""Add and Subtract Complex Numbers

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Simplify $(3+2i)+(1-4i)$ | $4-2i$ |
    """
    while True:
        a = random.randint(min_val, max_val)
        b = random.choice([n for n in range(min_val, max_val + 1) if n != 0])
        c = random.randint(min_val, max_val)
        d = random.choice([n for n in range(min_val, max_val + 1) if n != 0])
        operator = random.choice(["+", "-"])
        if operator == "+":
            p, q = a + c, b + d
        else:
            p, q = a - c, b - d
        if p != 0 and q != 0:
            break

    problem = (
        f"Simplify $({_complex_str(a, b)}){operator}({_complex_str(c, d)})$. "
        f"Format your answer as such: 4-2i."
    )
    solution = f"${_complex_result_str(p, q)}$"
    return problem, solution


@register
def alg2_rational_exponent(min_m=2, max_m=5):
    r"""Rational Exponents

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Evaluate $27^{2/3}$ | $9$ |
    """
    q = random.choice([2, 3])
    p = random.choice([pp for pp in (1, 2, 3) if pp != q])  # gcd(p, q) == 1
    m = random.randint(min_m, max_m)
    base = m ** q  # perfect q-th power so base^(p/q) is exactly m^p
    value = m ** p
    problem = f"Evaluate ${base}^{{{p}/{q}}}$"
    solution = f"${value}$"
    return problem, solution


@register
def alg2_solve_radical_equation(max_a=4, min_x=-5, max_x=5, max_c=8):
    r"""Solve a Radical Equation

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Solve $\sqrt{2x+3}=5$ for x | $x=11$ |
    """
    a = random.choice([n for n in range(-max_a, max_a + 1) if n != 0])
    x = random.randint(min_x, max_x)
    c = random.randint(0, max_c)  # c >= 0 so no extraneous root by construction
    b = c * c - a * x
    inside = f"{a}x{'+' if b >= 0 else '-'}{abs(b)}"
    problem = rf"Solve $\sqrt{{{inside}}}={c}$ for x"
    solution = f"$x={x}$"
    return problem, solution


@register
def alg2_solve_exponential_log(min_x=1, max_x=5):
    r"""Solve an Exponential Equation with Logarithms

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Solve $2^x=32$ for x | $x=5$ |
    """
    base = random.choice([2, 3, 5, 10])
    x = random.randint(min_x, max_x)
    value = base ** x
    problem = f"Solve ${base}^x={value}$ for x"
    solution = f"$x={x}$"
    return problem, solution


@register
def alg2_evaluate_log(min_exp=1, max_exp=5):
    r"""Evaluate a Logarithm

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Evaluate $\log_{2}(32)$ | $5$ |
    """
    base = random.choice([2, 3, 5, 10])
    exponent = random.randint(min_exp, max_exp)
    n = base ** exponent
    problem = rf"Evaluate $\log_{{{base}}}({n})$"
    solution = f"${exponent}$"
    return problem, solution


@register
def alg2_inverse_linear_function(max_m=6, max_b=10, min_t=-6, max_t=6):
    r"""Inverse of a Linear Function

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Given $f(x)=2x+3$, find $f^{-1}(11)$ | $4$ |
    """
    m = random.choice([n for n in range(-max_m, max_m + 1) if n != 0])
    b = random.choice([n for n in range(-max_b, max_b + 1) if n != 0])
    t = random.randint(min_t, max_t)  # the answer: f^{-1}(a) = t
    a = m * t + b
    problem = (
        f"Given $f(x)={m}x{'+' if b >= 0 else '-'}{abs(b)}$, find $f^{{-1}}({a})$"
    )
    solution = f"${t}$"
    return problem, solution


@register
def alg2_z_score(min_val=-20, max_val=20):
    r"""Z-Score

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | A value of $18$ comes from a distribution with mean $10$ and standard deviation $4$. Find its z-score. | $2$ |
    """
    mean = random.randint(min_val, max_val)
    sd = random.choice([1, 2, 4, 5, 8, 10])  # all give a terminating <=3dp z
    x = random.randint(min_val, max_val)
    z = (x - mean) / sd
    problem = (
        f"A value of ${x}$ comes from a distribution with mean ${mean}$ and "
        f"standard deviation ${sd}$. Find its z-score. "
        f"Round your answer to the nearest thousandth."
    )
    solution = f"${_clean_num(z)}$"
    return problem, solution


@register
def alg2_empirical_rule(min_mean=0, max_mean=100, min_sd=1, max_sd=15):
    r"""Empirical Rule (68-95-99.7)

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | In a normal distribution with mean $50$ and standard deviation $5$, approximately what percent of the data lies within $2$ standard deviation(s) of the mean? | 95% |
    """
    mean = random.randint(min_mean, max_mean)
    sd = random.randint(min_sd, max_sd)
    k = random.choice([1, 2, 3])
    percent = {1: "68%", 2: "95%", 3: "99.7%"}[k]
    problem = (
        f"In a normal distribution with mean ${mean}$ and standard deviation "
        f"${sd}$, approximately what percent of the data lies within ${k}$ "
        f"standard deviation(s) of the mean?"
    )
    solution = percent
    return problem, solution


@register
def alg2_solve_system_matrix(max_coeff=5, min_sol=-6, max_sol=6):
    r"""Solve a 2x2 Linear System

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Solve the system: $2x+3y=13$ and $1x-1y=1$ | $x=... , y=...$ |
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
    eq1 = f"{a}x{_signed(b, 'y')}={e}"
    eq2 = f"{c}x{_signed(d, 'y')}={f}"
    problem = (
        f"Solve the system: ${eq1}$ and ${eq2}$. "
        f"Format your answer as such: x=1, y=2."
    )
    solution = f"$x={x}, y={y}$"
    return problem, solution
