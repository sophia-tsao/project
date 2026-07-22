"""Solveki-local calculus generators.

Every generator here targets a computable gap in the Georgia "Calculus"
curriculum. Each takes no required arguments, returns a ``(problem, solution)``
pair of LaTeX strings, and produces a clean answer (integer, fraction, short
float, or short polynomial string). Names are prefixed ``calc_`` so they are
easy to scope.
"""
import math
import random
from fractions import Fraction

from ._registry import register
from ._format import num as _num
from .algebra import _format_polynomial

_FRACTION_HINT = "Express your answer as a fraction in the form a/b, or an integer."


# --- small polynomial helpers (poly represented as {exponent: coefficient}) ---

def _poly_eval(poly, x):
    """Evaluate ``poly`` at ``x`` (works for ints and Fractions)."""
    return sum(coeff * (x ** exp) for exp, coeff in poly.items())


def _poly_deriv(poly):
    """Return the derivative of ``poly`` as a new dict."""
    return {exp - 1: coeff * exp for exp, coeff in poly.items() if exp >= 1}


def _poly_mul(p, q):
    """Multiply two polynomials."""
    out = {}
    for e1, c1 in p.items():
        for e2, c2 in q.items():
            out[e1 + e2] = out.get(e1 + e2, 0) + c1 * c2
    return out


def _poly_add(p, q):
    """Add two polynomials."""
    out = dict(p)
    for exp, coeff in q.items():
        out[exp] = out.get(exp, 0) + coeff
    return out


def _poly_str(poly):
    """Render a poly dict via the shared algebra formatter."""
    terms = sorted(poly.items(), key=lambda kv: -kv[0])
    return _format_polynomial([(coeff, exp) for exp, coeff in terms])


def _fmt_frac(value):
    """Render a Fraction (or int) as ``"a/b"`` or ``"a"`` when whole."""
    fr = Fraction(value)
    if fr.denominator == 1:
        return str(fr.numerator)
    return f"{fr.numerator}/{fr.denominator}"


def _rand_poly(degree, lo=-5, hi=5):
    """A random poly of exactly ``degree`` (leading coeff nonzero)."""
    poly = {}
    for exp in range(degree + 1):
        poly[exp] = random.randint(lo, hi)
    lead = random.choice([c for c in range(lo, hi + 1) if c != 0])
    poly[degree] = lead
    return poly


# --------------------------------- limits ---------------------------------

@register
def calc_limit_rational(min_c=-4, max_c=4):
    r"""Limit of a Rational Function at a Point

    Either a removable discontinuity (shared linear factor cancels) or a
    direct substitution. Answer is an exact, reduced value.
    """
    c = random.randint(min_c, max_c)
    if random.random() < 0.5:
        # Removable: num = (x - c)*L1, den = (x - c)*L2 with L2(c) != 0.
        l1 = {1: random.choice([i for i in range(-4, 5) if i != 0]),
              0: random.randint(-5, 5)}
        while True:
            l2 = {1: random.choice([i for i in range(-4, 5) if i != 0]),
                  0: random.randint(-5, 5)}
            if _poly_eval(l2, c) != 0:
                break
        factor = {1: 1, 0: -c}
        num = _poly_mul(factor, l1)
        den = _poly_mul(factor, l2)
        ans = Fraction(_poly_eval(l1, c), _poly_eval(l2, c))
    else:
        # Direct substitution: den(c) != 0.
        num = _rand_poly(random.randint(1, 2))
        while True:
            den = _rand_poly(random.randint(1, 2))
            if _poly_eval(den, c) != 0:
                break
        ans = Fraction(_poly_eval(num, c), _poly_eval(den, c))

    problem = (
        f"Evaluate $\\lim_{{x \\to {c}}} "
        f"\\frac{{{_poly_str(num)}}}{{{_poly_str(den)}}}$. {_FRACTION_HINT}"
    )
    solution = f"${_fmt_frac(ans)}$"
    return problem, solution


# ------------------------------ derivatives -------------------------------

@register
def calc_derivative_polynomial(min_degree=2, max_degree=4):
    r"""Derivative of a Polynomial

    Solution is the derivative polynomial as a string.
    """
    poly = _rand_poly(random.randint(min_degree, max_degree))
    deriv = _poly_deriv(poly)
    problem = (
        f"Find the derivative of $f(x) = {_poly_str(poly)}$. "
        f"Write your answer as a polynomial, e.g. 3x^2-2x+1."
    )
    solution = f"${_poly_str(deriv)}$"
    return problem, solution


@register
def calc_product_rule(min_c=-4, max_c=4):
    r"""Product Rule at a Point

    Derivative of a product of two linear/quadratic factors, evaluated at a
    point for an exact numeric answer.
    """
    def factor():
        deg = random.randint(1, 2)
        return _rand_poly(deg, lo=-4, hi=4)

    f1, f2 = factor(), factor()
    c = random.randint(min_c, max_c)
    product = _poly_mul(f1, f2)
    ans = _poly_eval(_poly_deriv(product), c)
    problem = (
        f"Find the derivative of $f(x) = ({_poly_str(f1)})({_poly_str(f2)})$ "
        f"at $x = {c}$"
    )
    solution = f"${ans}$"
    return problem, solution


@register
def calc_quotient_rule(min_c=-4, max_c=4):
    r"""Quotient Rule at a Point

    Derivative of a (linear)/(linear) rational at a point, exact reduced
    fraction.
    """
    num = {1: random.choice([i for i in range(-5, 6) if i != 0]),
           0: random.randint(-5, 5)}
    c = random.randint(min_c, max_c)
    while True:
        den = {1: random.choice([i for i in range(-5, 6) if i != 0]),
               0: random.randint(-5, 5)}
        if _poly_eval(den, c) != 0:
            break
    # (num' den - num den') / den^2
    numd, dend = _poly_deriv(num), _poly_deriv(den)
    top = (_poly_eval(numd, c) * _poly_eval(den, c)
           - _poly_eval(num, c) * _poly_eval(dend, c))
    bottom = _poly_eval(den, c) ** 2
    ans = Fraction(top, bottom)
    problem = (
        f"Find the derivative of $f(x) = "
        f"\\frac{{{_poly_str(num)}}}{{{_poly_str(den)}}}$ at $x = {c}$. "
        f"{_FRACTION_HINT}"
    )
    solution = f"${_fmt_frac(ans)}$"
    return problem, solution


@register
def calc_chain_rule(min_c=-3, max_c=3, max_power=4):
    r"""Chain Rule at a Point

    Derivative of $(ax+b)^n$ evaluated at a point, exact numeric.
    """
    a = random.choice([i for i in range(-3, 4) if i != 0])
    b = random.randint(-4, 4)
    n = random.randint(2, max_power)
    c = random.randint(min_c, max_c)
    inner = {1: a, 0: b}
    ans = n * a * (_poly_eval(inner, c) ** (n - 1))
    problem = (
        f"Find the derivative of $f(x) = ({_poly_str(inner)})^{{{n}}}$ "
        f"at $x = {c}$"
    )
    solution = f"${ans}$"
    return problem, solution


@register
def calc_derivative_exp_log_trig():
    r"""Derivative of an Exponential, Logarithmic, or Trig Function

    One of $a e^{kx}$, $a \ln(x)$, $a \sin(kx)$, or $a \cos(kx)$, evaluated
    at a point and reported to 3 decimal places.
    """
    kind = random.choice(["exp", "ln", "sin", "cos"])
    a = random.choice([i for i in range(-6, 7) if i != 0])
    if kind == "ln":
        c = random.randint(1, 6)
        expr = f"{a} \\ln(x)"
        value = a / c
    else:
        k = random.choice([i for i in range(-3, 4) if i != 0])
        c = random.randint(-3, 3)
        if kind == "exp":
            expr = f"{a} e^{{{k} x}}"
            value = a * k * math.exp(k * c)
        elif kind == "sin":
            expr = f"{a} \\sin({k} x)"
            value = a * k * math.cos(k * c)
        else:  # cos
            expr = f"{a} \\cos({k} x)"
            value = -a * k * math.sin(k * c)
    problem = (
        f"Find the derivative of $f(x) = {expr}$ at $x = {c}$. "
        f"Round your answer to the nearest thousandth."
    )
    solution = f"${_num(value)}$"
    return problem, solution


@register
def calc_higher_order_derivative(min_c=-3, max_c=3):
    r"""Higher-Order Derivative at a Point

    The n-th derivative of a polynomial evaluated at a point, exact numeric.
    """
    order = random.randint(2, 3)
    degree = random.randint(order, order + 2)
    poly = _rand_poly(degree)
    d = poly
    for _ in range(order):
        d = _poly_deriv(d)
    c = random.randint(min_c, max_c)
    ans = _poly_eval(d, c) if d else 0
    ordinal = {2: "2nd", 3: "3rd"}[order]
    problem = (
        f"Find the {ordinal} derivative of $f(x) = {_poly_str(poly)}$ "
        f"at $x = {c}$"
    )
    solution = f"${ans}$"
    return problem, solution


# ------------------------- applications of derivatives --------------------

@register
def calc_tangent_line(min_c=-3, max_c=3):
    r"""Tangent Line to a Polynomial at a Point

    Solution is the line ``y = m x + b``.
    """
    poly = _rand_poly(random.randint(2, 3))
    c = random.randint(min_c, max_c)
    m = _poly_eval(_poly_deriv(poly), c)
    b = _poly_eval(poly, c) - m * c
    rhs = _poly_str({1: m, 0: b})
    problem = (
        f"Find the tangent line to $f(x) = {_poly_str(poly)}$ at $x = {c}$. "
        f"Write your answer in the form y = mx+b."
    )
    solution = f"$y = {rhs}$"
    return problem, solution


@register
def calc_extrema(min_root=-5, max_root=5):
    r"""Critical Points via the First Derivative

    Critical x-values of a quadratic or cubic, sorted, as ``x = a, b``.
    """
    if random.random() < 0.5:
        # Quadratic with an integer critical point.
        a = random.choice([i for i in range(-4, 5) if i != 0])
        r = random.randint(min_root, max_root)
        poly = {2: a, 1: -2 * a * r, 0: random.randint(-5, 5)}
        roots = [r]
    else:
        # Cubic with two distinct integer critical points.
        while True:
            r1 = random.randint(min_root, max_root)
            r2 = random.randint(min_root, max_root)
            if r1 != r2 and (r1 + r2) % 2 == 0:
                break
        r1, r2 = sorted((r1, r2))
        a = random.choice([i for i in range(-3, 4) if i != 0])
        b = -3 * a * (r1 + r2) // 2
        c = 3 * a * r1 * r2
        poly = {3: a, 2: b, 1: c, 0: random.randint(-5, 5)}
        roots = [r1, r2]
    xs = ", ".join(str(x) for x in sorted(roots))
    problem = (
        f"Find the critical points of $f(x) = {_poly_str(poly)}$. "
        f"Give the x-value(s) as integers or fractions a/b, comma-separated "
        f"and in increasing order."
    )
    solution = f"$x = {xs}$"
    return problem, solution


@register
def calc_inflection_point(max_coeff=6):
    r"""Inflection Point of a Cubic via the Second Derivative

    Reports the exact reduced x-value of the inflection point.
    """
    a = random.choice([i for i in range(-4, 5) if i != 0])
    b = random.randint(-max_coeff, max_coeff)
    c = random.randint(-max_coeff, max_coeff)
    d = random.randint(-max_coeff, max_coeff)
    poly = {3: a, 2: b, 1: c, 0: d}
    # f'' = 6a x + 2b -> x = -b / (3a)
    ans = Fraction(-b, 3 * a)
    problem = (
        f"Find the inflection point of $f(x) = {_poly_str(poly)}$. "
        f"Give the x-value as an integer or fraction a/b. {_FRACTION_HINT}"
    )
    solution = f"$x = {_fmt_frac(ans)}$"
    return problem, solution


# -------------------------------- integrals -------------------------------

@register
def calc_definite_integral_poly():
    r"""Definite Integral of a Polynomial

    Exact value over ``[a, b]``.
    """
    poly = _rand_poly(random.randint(1, 3))
    a = random.randint(-4, 3)
    b = random.randint(a + 1, 5)
    total = sum(
        Fraction(coeff * (b ** (exp + 1) - a ** (exp + 1)), exp + 1)
        for exp, coeff in poly.items()
    )
    problem = (
        f"Evaluate $\\int_{{{a}}}^{{{b}}} {_poly_str(poly)} \\, dx$. "
        f"{_FRACTION_HINT}"
    )
    solution = f"${_fmt_frac(total)}$"
    return problem, solution


@register
def calc_indefinite_integral_poly():
    r"""Indefinite Integral of a Polynomial

    Antiderivative (with ``+ C``) has clean integer coefficients by
    construction.
    """
    degree = random.randint(1, 3)
    poly = {}
    anti = {}
    for exp in range(degree + 1):
        m = random.randint(-4, 4)
        if exp == degree and m == 0:
            m = random.choice([-2, -1, 1, 2])
        poly[exp] = m * (exp + 1)      # integrates to m*x^(exp+1)
        anti[exp + 1] = m
    problem = (
        f"Find the indefinite integral $\\int {_poly_str(poly)} \\, dx$. "
        f"Write your answer as a polynomial plus C, e.g. x^2+3x + C."
    )
    solution = f"${_poly_str(anti)} + C$"
    return problem, solution


@register
def calc_usub_integral():
    r"""Definite Integral by u-Substitution

    $\int_p^q (ax+b)^n \, dx$, exact value.
    """
    a = random.choice([i for i in range(-3, 4) if i != 0])
    b = random.randint(-4, 4)
    n = random.randint(2, 4)
    p = random.randint(-3, 2)
    q = random.randint(p + 1, 4)
    upper = (a * q + b) ** (n + 1)
    lower = (a * p + b) ** (n + 1)
    ans = Fraction(upper - lower, a * (n + 1))
    inner = _poly_str({1: a, 0: b})
    problem = (
        f"Evaluate $\\int_{{{p}}}^{{{q}}} ({inner})^{{{n}}} \\, dx$. "
        f"{_FRACTION_HINT}"
    )
    solution = f"${_fmt_frac(ans)}$"
    return problem, solution


@register
def calc_area_between_curves():
    r"""Area Between Two Curves

    Two polynomials that meet at the endpoints ``a`` and ``b`` (so one stays
    above the other on the interval). Exact area.
    """
    a = random.randint(-3, 2)
    b = random.randint(a + 1, 4)
    g = _rand_poly(random.randint(0, 2), lo=-3, hi=3)
    c = random.choice([-3, -2, -1])        # C < 0 -> f - g >= 0 on [a, b]
    diff = _poly_mul({1: c}, _poly_mul({1: 1, 0: -a}, {1: 1, 0: -b}))
    f = _poly_add(g, diff)
    # area = integral of (f - g) = integral of diff over [a, b]
    area = sum(
        Fraction(coeff * (b ** (exp + 1) - a ** (exp + 1)), exp + 1)
        for exp, coeff in diff.items()
    )
    problem = (
        f"Find the area between $f(x) = {_poly_str(f)}$ and "
        f"$g(x) = {_poly_str(g)}$ over $[{a}, {b}]$. {_FRACTION_HINT}"
    )
    solution = f"${_fmt_frac(abs(area))}$"
    return problem, solution


@register
def calc_average_value():
    r"""Average Value of a Function

    $\frac{1}{b-a}\int_a^b f(x)\,dx$ for a polynomial. Exact.
    """
    poly = _rand_poly(random.randint(1, 3))
    a = random.randint(-4, 3)
    b = random.randint(a + 1, 5)
    integral = sum(
        Fraction(coeff * (b ** (exp + 1) - a ** (exp + 1)), exp + 1)
        for exp, coeff in poly.items()
    )
    ans = integral / (b - a)
    problem = (
        f"Find the average value of $f(x) = {_poly_str(poly)}$ on $[{a}, {b}]$. "
        f"{_FRACTION_HINT}"
    )
    solution = f"${_fmt_frac(ans)}$"
    return problem, solution


@register
def calc_riemann_sum():
    r"""Left or Right Riemann Sum

    A polynomial on ``[a, b]`` with ``n`` rectangles. Exact value.
    """
    side = random.choice(["left", "right"])
    poly = _rand_poly(random.randint(1, 2), lo=-3, hi=3)
    a = random.randint(-3, 2)
    b = random.randint(a + 1, 4)
    n = random.randint(2, 6)
    dx = Fraction(b - a, n)
    indices = range(n) if side == "left" else range(1, n + 1)
    total = sum(_poly_eval(poly, a + i * dx) for i in indices)
    ans = dx * total
    problem = (
        f"Find the {side} Riemann sum of $f(x) = {_poly_str(poly)}$ on "
        f"$[{a}, {b}]$ using ${n}$ rectangles. {_FRACTION_HINT}"
    )
    solution = f"${_fmt_frac(ans)}$"
    return problem, solution
