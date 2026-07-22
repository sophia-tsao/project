"""Solveki-local pre-algebra generators (Georgia grade 6-8 topics).

Every generator name starts with ``pre_`` and returns a ``(problem, solution)``
pair of LaTeX-wrapped strings. Answers are kept clean: integers, short decimals
(<=3 dp), or reduced ``\\frac{p}{q}`` fractions.
"""
import math
import random
from fractions import Fraction

from ._registry import register
from ._format import frac_from, num
from .algebra import _format_polynomial

# Inequality relation tokens and their reversal. The problem statement renders
# LaTeX (``\leq``/``\geq``); solutions use typeable ASCII (``<=``/``>=``).
_FLIP = {"<": ">", ">": "<", "\\leq": "\\geq", "\\geq": "\\leq"}
_OPS = list(_FLIP)
# Map a LaTeX relation token to the typeable ASCII the student would type.
_ASCII_OP = {"<": "<", ">": ">", "\\leq": "<=", "\\geq": ">="}

_FRACTION_HINT = "Express your answer as a fraction in the form a/b, or an integer."


def _signed(mag_value):
    """Return a ``' + n'`` / ``' - n'`` display fragment for a signed int."""
    if mag_value >= 0:
        return f"+ {mag_value}"
    return f"- {abs(mag_value)}"


def _frac_solution(fr):
    """Render a ``Fraction`` typeably as ``$p$`` (integer) or ``$p/q$``."""
    return f"${frac_from(fr)}$"


@register
def pre_unit_rate(min_rate=2, max_rate=30, min_time=2, max_time=12):
    r"""Unit Rate

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | A vehicle travels $120$ miles in $3$ hours. Find the unit rate in miles per hour. | $40$ |
    """
    rate = random.randint(min_rate, max_rate)
    t = random.randint(min_time, max_time)
    d = rate * t
    problem = (
        f"A vehicle travels ${d}$ miles in ${t}$ hours. "
        f"Find the unit rate in miles per hour."
    )
    return problem, f"${rate}$"


@register
def pre_equivalent_ratio(min_term=1, max_term=9, min_factor=2, max_factor=9):
    r"""Equivalent Ratio

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Fill in the blank to make the ratios equivalent: $2:5 = 6:\square$ | $15$ |
    """
    a = random.randint(min_term, max_term)
    b = random.randint(min_term, max_term)
    f = random.randint(min_factor, max_factor)
    c = a * f
    d = b * f
    problem = (
        f"Fill in the blank to make the ratios equivalent: "
        f"${a}:{b} = {c}:\\square$"
    )
    return problem, f"${d}$"


@register
def pre_solve_proportion(min_term=1, max_term=12, min_factor=1, max_factor=9):
    r"""Solve a Proportion

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Solve for $x$: $\frac{2}{3} = \frac{x}{9}$ | $6$ |
    """
    a = random.randint(min_term, max_term)
    b = random.randint(min_term, max_term)
    k = random.randint(min_factor, max_factor)
    d = b * k
    x = a * k
    problem = f"Solve for $x$: $\\frac{{{a}}}{{{b}}} = \\frac{{x}}{{{d}}}$"
    return problem, f"${x}$"


@register
def pre_integer_operations(min_val=-20, max_val=20, max_quotient=12):
    r"""Signed Integer Operations

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Evaluate $(-6) \times (4)$ | $-24$ |
    """
    op = random.choice(["+", "-", "\\times", "\\div"])
    if op == "\\div":
        b = random.choice([i for i in range(-12, 13) if i != 0])
        quotient = random.randint(-max_quotient, max_quotient)
        a = b * quotient
        result = quotient
    else:
        a = random.randint(min_val, max_val)
        b = random.randint(min_val, max_val)
        if op == "+":
            result = a + b
        elif op == "-":
            result = a - b
        else:
            result = a * b
    problem = f"Evaluate $({a}) {op} ({b})$"
    return problem, f"${result}$"


@register
def pre_rational_operations(min_num=-9, max_num=9, min_den=2, max_den=9):
    r"""Signed Fraction Operations

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Evaluate $\frac{1}{2} + \frac{-1}{3}$ | $1/6$ |
    """
    op = random.choice(["+", "-", "\\times", "\\div"])
    a = random.choice([i for i in range(min_num, max_num + 1) if i != 0])
    b = random.randint(min_den, max_den)
    c = random.choice([i for i in range(min_num, max_num + 1) if i != 0])
    d = random.randint(min_den, max_den)
    f1 = Fraction(a, b)
    f2 = Fraction(c, d)
    if op == "+":
        result = f1 + f2
    elif op == "-":
        result = f1 - f2
    elif op == "\\times":
        result = f1 * f2
    else:
        result = f1 / f2
    problem = (
        f"Evaluate $\\frac{{{a}}}{{{b}}} {op} \\frac{{{c}}}{{{d}}}$. {_FRACTION_HINT}"
    )
    return problem, _frac_solution(result)


@register
def pre_absolute_value(min_val=-20, max_val=20):
    r"""Absolute Value Expression

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Evaluate $|3 - 8|$ | $5$ |
    """
    if random.random() < 0.5:
        a = random.randint(max(0, min_val), max_val)
        b = random.randint(max(0, min_val), max_val)
        problem = f"Evaluate $|{a} - {b}|$"
        result = abs(a - b)
    else:
        a = random.randint(min_val, max_val)
        b = random.randint(min_val, max_val)
        problem = f"Evaluate $|{a}| + |{b}|$"
        result = abs(a) + abs(b)
    return problem, f"${result}$"


@register
def pre_one_step_inequality():
    r"""One-Step Inequality

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Solve the inequality: $x + 3 < 8$ | $x < 5$ |
    """
    op = random.choice(_OPS)
    if random.random() < 0.5:
        # Additive: x + a  op  b  ->  x op (b - a). No sign flip.
        a = random.choice([i for i in range(-10, 11) if i != 0])
        b = random.randint(-20, 20)
        c = b - a
        problem = f"Solve the inequality: $x {_signed(a)} {op} {b}$"
        solution = f"$x {_ASCII_OP[op]} {c}$"
    else:
        # Multiplicative: k*x op b  ->  x op' (b/k). Flip op when k < 0.
        k = random.choice([i for i in range(-10, 11) if abs(i) >= 2])
        c = random.randint(-15, 15)
        b = k * c
        out_op = _FLIP[op] if k < 0 else op
        problem = f"Solve the inequality: ${k}x {op} {b}$"
        solution = f"$x {_ASCII_OP[out_op]} {c}$"
    return problem, solution


@register
def pre_multi_step_inequality():
    r"""Multi-Step Inequality

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Solve the inequality: $3x + 4 \leq 19$ | $x \leq 5$ |
    """
    op = random.choice(_OPS)
    a = random.choice([i for i in range(-10, 11) if abs(i) >= 2])
    b = random.randint(-20, 20)
    r = random.randint(-15, 15)
    c = a * r + b
    out_op = _FLIP[op] if a < 0 else op
    problem = f"Solve the inequality: ${a}x {_signed(b)} {op} {c}$"
    solution = f"$x {_ASCII_OP[out_op]} {r}$"
    return problem, solution


def _normalize_sci(fr):
    """Return ``(mantissa, exponent)`` for a positive ``Fraction`` value.

    Mantissa lands in ``[1, 10)`` and is rounded to 3 dp.
    """
    ten = Fraction(10)
    x = fr
    exp = 0
    while x >= ten:
        x /= ten
        exp += 1
    while x < 1:
        x *= ten
        exp -= 1
    return round(float(x), 3), exp


@register
def pre_scientific_notation_ops():
    r"""Scientific Notation Operations

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | $3.0 \times 10^{4} + 2.0 \times 10^{4}$ | $5.0 \times 10^{4}$ |
    """
    ten = Fraction(10)
    while True:
        op = random.choice(["+", "-", "\\div"])
        if op in ("+", "-"):
            e = random.randint(-3, 6)
            e1 = e2 = e
            m1t = random.randint(10, 99)
            m2t = random.randint(10, 99)
            if op == "-":
                if m1t <= m2t:
                    continue
        else:
            e1 = random.randint(-3, 6)
            e2 = random.randint(-3, 6)
            m1t = random.randint(10, 99)
            m2t = random.randint(10, 99)
        f1 = Fraction(m1t, 10) * (ten ** e1)
        f2 = Fraction(m2t, 10) * (ten ** e2)
        if op == "+":
            value = f1 + f2
        elif op == "-":
            value = f1 - f2
        else:
            value = f1 / f2
        if value <= 0:
            continue
        mant, exp = _normalize_sci(value)
        if mant < 1.0 or mant >= 10.0:
            continue
        m1 = m1t / 10
        m2 = m2t / 10
        problem = (
            f"Evaluate ${m1:.1f} \\times 10^{{{e1}}} {op} "
            f"{m2:.1f} \\times 10^{{{e2}}}$. "
            f"Answers should be formatted as such: 5.0*10^4."
        )
        solution = f"${mant}*10^{exp}$"
        return problem, solution


@register
def pre_integer_exponent_rules(min_base=2, max_base=9, min_exp=-4, max_exp=4):
    r"""Integer Exponent Rules

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Simplify: $2^{3} \times 2^{-1}$ | $2^2$ |
    """
    a = random.randint(min_base, max_base)
    m = random.randint(min_exp, max_exp)
    n = random.randint(min_exp, max_exp)
    kind = random.choice(["mult", "div", "power"])
    if kind == "mult":
        problem = f"Simplify: ${a}^{{{m}}} \\times {a}^{{{n}}}$"
        r = m + n
    elif kind == "div":
        problem = f"Simplify: ${a}^{{{m}}} \\div {a}^{{{n}}}$"
        r = m - n
    else:
        problem = f"Simplify: $({a}^{{{m}}})^{{{n}}}$"
        r = m * n
    problem += " Answers should be formatted as such: 2^3."
    return problem, f"${a}^{r}$"


@register
def pre_constant_of_proportionality(max_k=12, min_x=2, max_x=12):
    r"""Constant of Proportionality

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | The variable $y$ varies directly with $x$. When $x = 4$, $y = 12$. Find the constant of proportionality $k$. | $3$ |
    """
    k = random.choice([i for i in range(-max_k, max_k + 1) if i != 0])
    x = random.randint(min_x, max_x)
    y = k * x
    problem = (
        f"The variable $y$ varies directly with $x$. "
        f"When $x = {x}$, $y = {y}$. "
        f"Find the constant of proportionality $k$."
    )
    return problem, f"${k}$"


@register
def pre_evaluate_function(min_coeff=-9, max_coeff=9, min_x=-6, max_x=6):
    r"""Evaluate a Function

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Given $f(x)=2x+3$, evaluate $f(4)$. | $11$ |
    """
    v = random.randint(min_x, max_x)
    nonzero = [i for i in range(min_coeff, max_coeff + 1) if i != 0]
    if random.random() < 0.5:
        a = random.choice(nonzero)
        b = random.randint(min_coeff, max_coeff)
        terms = [(a, 1), (b, 0)]
    else:
        a = random.choice(nonzero)
        b = random.randint(min_coeff, max_coeff)
        c = random.randint(min_coeff, max_coeff)
        terms = [(a, 2), (b, 1), (c, 0)]
    poly = _format_polynomial(terms)
    result = sum(coeff * (v ** exp) for coeff, exp in terms)
    problem = f"Given $f(x)={poly}$, evaluate $f({v})$."
    return problem, f"${result}$"


@register
def pre_slope_from_two_points(coord_min=-10, coord_max=10):
    r"""Slope from Two Points

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Find the slope of the line through the points $(1, 2)$ and $(3, 8)$. | $3$ |
    """
    x1 = random.randint(coord_min, coord_max)
    x2 = random.randint(coord_min, coord_max)
    while x2 == x1:
        x2 = random.randint(coord_min, coord_max)
    y1 = random.randint(coord_min, coord_max)
    y2 = random.randint(coord_min, coord_max)
    slope = Fraction(y2 - y1, x2 - x1)
    problem = (
        f"Find the slope of the line through the points "
        f"$({x1}, {y1})$ and $({x2}, {y2})$. {_FRACTION_HINT}"
    )
    return problem, _frac_solution(slope)


@register
def pre_linear_function_value(min_val=-10, max_val=10):
    r"""Linear Function Value

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | A line has slope $m = 2$ and y-intercept $b = 3$. Find $y$ when $x = 4$. | $11$ |
    """
    m = random.choice([i for i in range(min_val, max_val + 1) if i != 0])
    b = random.randint(min_val, max_val)
    x = random.randint(min_val, max_val)
    y = m * x + b
    problem = (
        f"A line has slope $m = {m}$ and y-intercept $b = {b}$. "
        f"Find $y$ when $x = {x}$."
    )
    return problem, f"${y}$"


@register
def pre_mean_absolute_deviation(min_val=1, max_val=20):
    r"""Mean Absolute Deviation

    Convention: mean = sum/n (chosen so it is an integer); MAD is the mean of
    the absolute deviations from that mean.

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Find the mean absolute deviation of the data set: $2, 4, 6, 8$. | $2$ |
    """
    n = random.choice([4, 5])
    while True:
        data = [random.randint(min_val, max_val) for _ in range(n)]
        if sum(data) % n == 0:
            break
    mean = sum(data) / n
    mad = sum(abs(v - mean) for v in data) / n
    data_str = ", ".join(str(v) for v in data)
    problem = (
        f"Find the mean absolute deviation of the data set: ${data_str}$. "
        f"Round your answer to the nearest thousandth."
    )
    return problem, f"${num(mad)}$"


@register
def pre_interquartile_range(min_val=1, max_val=30):
    r"""Interquartile Range

    Convention: sort the 7 values; Q1 is the median of the lower 3 (index 1),
    Q3 is the median of the upper 3 (index 5); IQR = Q3 - Q1.

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Find the interquartile range (IQR) of the data set: $3, 5, 7, 8, 10, 12, 15$. | $7$ |
    """
    data = [random.randint(min_val, max_val) for _ in range(7)]
    s = sorted(data)
    iqr = s[5] - s[1]
    data_str = ", ".join(str(v) for v in data)
    problem = (
        f"Find the interquartile range (IQR) of the data set: ${data_str}$."
    )
    return problem, f"${iqr}$"


@register
def pre_approximate_irrational(min_n=2, max_n=120):
    r"""Approximate an Irrational Square Root

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Approximate $\sqrt{50}$ to the nearest tenth. | $7.1$ |
    """
    while True:
        n = random.randint(min_n, max_n)
        root = math.sqrt(n)
        if root == int(root):
            continue  # skip perfect squares
        scaled = root * 10
        # Reject values that sit ambiguously on a rounding boundary.
        if abs(scaled - (math.floor(scaled) + 0.5)) < 1e-6:
            continue
        problem = f"Approximate $\\sqrt{{{n}}}$ to the nearest tenth."
        return problem, f"${num(root, 1)}$"
