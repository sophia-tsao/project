"""Solveki-local generators for Georgia "Precalculus".

Every generator here takes no required arguments, is decorated with
``@register``, and returns a ``(problem, solution)`` pair of LaTeX strings.
Answers are kept clean: integers, values rounded to at most three decimal
places, or reduced ``"a/b"`` fractions. Never seed ``random`` inside a
generator.
"""
import random
from fractions import Fraction
from math import atan2, cos, degrees, gcd, hypot, radians, sin, sqrt, tan

from ._registry import register
from ._format import num as _num

_ROUND_HINT = "Round your answer to the nearest thousandth."


# Primitive Pythagorean triples (leg, leg, hypotenuse), used where an exact
# rational trig value is required.
_PYTHAG_TRIPLES = [
    (3, 4, 5),
    (5, 12, 13),
    (8, 15, 17),
    (7, 24, 25),
    (20, 21, 29),
    (9, 40, 41),
    (12, 35, 37),
]

# Special exact values as (LaTeX, numeric) pairs, grouped by the trig context.
_R2 = sqrt(2) / 2
_R3 = sqrt(3) / 2
_SIN_COS_VALUES = [
    (r"0", 0.0),
    (r"\frac{1}{2}", 0.5),
    (r"\frac{\sqrt{2}}{2}", _R2),
    (r"\frac{\sqrt{3}}{2}", _R3),
    (r"1", 1.0),
    (r"-\frac{1}{2}", -0.5),
    (r"-\frac{\sqrt{2}}{2}", -_R2),
    (r"-\frac{\sqrt{3}}{2}", -_R3),
    (r"-1", -1.0),
]
_TAN_VALUES = [
    (r"0", 0.0),
    (r"\frac{\sqrt{3}}{3}", sqrt(3) / 3),
    (r"1", 1.0),
    (r"\sqrt{3}", sqrt(3)),
    (r"-\frac{\sqrt{3}}{3}", -sqrt(3) / 3),
    (r"-1", -1.0),
    (r"-\sqrt{3}", -sqrt(3)),
]


def _format_poly(terms, var):
    """Render ``(coefficient, exponent)`` pairs as a polynomial string.

    ``terms`` is ordered from the highest exponent down. Zero-coefficient
    terms are dropped and unit coefficients omit the leading ``1``.
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
            token = var if exp == 1 else f"{var}^{exp}"
            body = token if magnitude == 1 else f"{magnitude}{token}"
        pieces.append((sign, body))

    if not pieces:
        return "0"

    first_sign, first_body = pieces[0]
    result = first_body if first_sign == "+" else f"-{first_body}"
    for sign, body in pieces[1:]:
        result += f"{sign}{body}"
    return result


@register
def pc_law_of_sines(min_angle=25, max_angle=80, min_side=3, max_side=25):
    r"""Law of Sines (ASA)

    Given two angles and a side, find another side via
    ``b = a * sin(B) / sin(A)``.
    """
    angle_a = random.randint(min_angle, max_angle)
    angle_b = random.randint(min_angle, max_angle)
    side_a = random.randint(min_side, max_side)
    ans = side_a * sin(radians(angle_b)) / sin(radians(angle_a))
    problem = (
        f"In triangle $ABC$, angle $A = {angle_a}^\\circ$, angle "
        f"$B = {angle_b}^\\circ$, and side $a = {side_a}$ (opposite $A$). "
        f"Find side $b$ (opposite $B$), rounded to the nearest thousandth."
    )
    return problem, f"${_num(ans)}$"


@register
def pc_law_of_cosines_side(min_side=3, max_side=20, min_angle=20, max_angle=160):
    r"""Law of Cosines (SAS)

    Given two sides and the included angle, find the third side via
    ``c^2 = a^2 + b^2 - 2ab*cos(C)``.
    """
    side_a = random.randint(min_side, max_side)
    side_b = random.randint(min_side, max_side)
    angle_c = random.randint(min_angle, max_angle)
    c_sq = side_a ** 2 + side_b ** 2 - 2 * side_a * side_b * cos(radians(angle_c))
    ans = sqrt(c_sq)
    problem = (
        f"In triangle $ABC$, side $a = {side_a}$, side $b = {side_b}$, and the "
        f"included angle $C = {angle_c}^\\circ$. Find side $c$, rounded to the "
        f"nearest thousandth."
    )
    return problem, f"${_num(ans)}$"


@register
def pc_oblique_triangle_area(min_side=3, max_side=20, min_angle=20, max_angle=160):
    r"""Oblique Triangle Area (SAS)

    Area of a triangle from two sides and the included angle:
    ``0.5 * a * b * sin(C)``.
    """
    side_a = random.randint(min_side, max_side)
    side_b = random.randint(min_side, max_side)
    angle_c = random.randint(min_angle, max_angle)
    ans = 0.5 * side_a * side_b * sin(radians(angle_c))
    problem = (
        f"A triangle has sides $a = {side_a}$ and $b = {side_b}$ with included "
        f"angle $C = {angle_c}^\\circ$. Find its area, rounded to the nearest "
        f"thousandth."
    )
    return problem, f"${_num(ans)}$"


@register
def pc_inverse_trig():
    r"""Inverse Trigonometric Values

    Evaluate arcsin/arccos/arctan at a special value; answer in degrees.
    """
    func = random.choice(["sin", "cos", "tan"])
    if func == "tan":
        latex, value = random.choice(_TAN_VALUES)
        deg = round(degrees(atan2(value, 1.0)))
    else:
        latex, value = random.choice(_SIN_COS_VALUES)
        from math import acos, asin
        deg = round(degrees(asin(value) if func == "sin" else acos(value)))
    problem = f"Evaluate $\\arc{func}\\left({latex}\\right)$ in degrees."
    return problem, f"${deg}$"


@register
def pc_double_angle():
    r"""Double-Angle Values

    Given ``sin x`` or ``cos x`` (from a Pythagorean triple, x acute), compute
    ``sin(2x)`` or ``cos(2x)`` as a reduced fraction.
    """
    a, b, c = random.choice(_PYTHAG_TRIPLES)
    # Randomly decide which leg plays the "opposite" role for sin.
    if random.random() < 0.5:
        a, b = b, a
    given = random.choice(["sin", "cos"])
    if given == "sin":
        given_num = a  # sin x = a/c  ->  cos x = b/c
    else:
        given_num = b  # cos x = b/c  ->  sin x = a/c
    sin_num, cos_num = a, b  # over c
    target = random.choice(["sin", "cos"])
    if target == "sin":
        frac = Fraction(2 * sin_num * cos_num, c * c)
    else:
        frac = Fraction(cos_num * cos_num - sin_num * sin_num, c * c)
    problem = (
        f"Given that $\\{given} x = \\frac{{{given_num}}}{{{c}}}$ and $x$ is "
        f"acute, find $\\{target}(2x)$. Express your answer as a reduced "
        f"fraction a/b."
    )
    return problem, f"${frac.numerator}/{frac.denominator}$"


def _solve_trig(func_numeric, value, is_tan):
    """Integer-degree solutions of ``f(x) = value`` on ``[0, 360)``."""
    sols = []
    for d in range(360):
        if is_tan and d in (90, 270):
            continue
        if abs(func_numeric(radians(d)) - value) < 1e-6:
            sols.append(d)
    return sols


@register
def pc_solve_trig_equation():
    r"""Solve a Trigonometric Equation

    Solve ``sin/cos/tan(x) = value`` on ``[0, 360)`` degrees.
    """
    func = random.choice(["sin", "cos", "tan"])
    if func == "tan":
        latex, value = random.choice(_TAN_VALUES)
        sols = _solve_trig(tan, value, True)
    else:
        latex, value = random.choice(_SIN_COS_VALUES)
        fn = sin if func == "sin" else cos
        sols = _solve_trig(fn, value, False)
    problem = (
        f"Solve $\\{func}(x) = {latex}$ for $x$ in $[0, 360)$ degrees. "
        f"List all solutions in degrees, comma-separated and in increasing "
        f"order."
    )
    return problem, "$" + ", ".join(str(d) for d in sorted(sols)) + "$"


def _clean(value):
    """Round to 3 dp and normalise ``-0.0`` to ``0.0``."""
    return round(value, 3) + 0.0


def _pt(value):
    """Typeable coordinate component: 3dp, trailing ``.0`` dropped."""
    return _num(value)


@register
def pc_polar_to_rectangular(max_r=10):
    r"""Polar to Rectangular

    Convert ``(r, theta_deg)`` to rectangular ``(x, y)``.
    """
    r = random.randint(1, max_r)
    theta = random.choice([0, 30, 45, 60, 90, 120, 135, 150, 180,
                            210, 225, 240, 270, 300, 315, 330])
    x = r * cos(radians(theta))
    y = r * sin(radians(theta))
    problem = (
        f"Convert the polar coordinates $(r, \\theta) = ({r}, {theta}^\\circ)$ "
        f"to rectangular coordinates, rounded to the nearest thousandth. "
        f"Format your answer as (x, y)."
    )
    return problem, f"({_pt(x)}, {_pt(y)})"


@register
def pc_rectangular_to_polar(max_coord=10):
    r"""Rectangular to Polar

    Convert ``(x, y)`` to polar ``(r, theta_deg)`` with ``0 <= theta < 360``.
    """
    while True:
        x = random.randint(-max_coord, max_coord)
        y = random.randint(-max_coord, max_coord)
        if x != 0 or y != 0:
            break
    r = hypot(x, y)
    theta = degrees(atan2(y, x))
    if theta < 0:
        theta += 360
    problem = (
        f"Convert the rectangular coordinates $(x, y) = ({x}, {y})$ to polar "
        f"coordinates $(r, \\theta)$ with $\\theta$ in degrees, "
        f"$0 \\le \\theta < 360$, rounded to the nearest thousandth. "
        f"Format your answer as (r, theta)."
    )
    return problem, f"({_pt(r)}, {_pt(theta)})"


@register
def pc_finite_geometric_sum(max_a=6, max_n=8):
    r"""Finite Geometric Series Sum

    Sum of the first ``n`` terms with first term ``a`` and ratio ``r``.
    """
    a = random.choice([i for i in range(-max_a, max_a + 1) if i != 0])
    r = random.choice([-3, -2, 2, 3])
    n = random.randint(2, max_n)
    total = sum(a * r ** k for k in range(n))
    problem = (
        f"Find the sum of the first ${n}$ terms of the geometric series with "
        f"first term $a = {a}$ and common ratio $r = {r}$."
    )
    return problem, f"${total}$"


@register
def pc_sigma_arithmetic_sum(max_coeff=5, max_const=10, max_n=20):
    r"""Sigma-Notation Arithmetic Sum

    Evaluate ``sum_{k=1}^{n} (A*k + B)``.
    """
    coeff = random.randint(1, max_coeff)
    const = random.randint(-max_const, max_const)
    n = random.randint(3, max_n)
    total = sum(coeff * k + const for k in range(1, n + 1))
    term = f"{coeff}k"
    if const > 0:
        term += f" + {const}"
    elif const < 0:
        term += f" - {abs(const)}"
    problem = f"Evaluate $\\sum_{{k=1}}^{{{n}}} ({term})$."
    return problem, f"${total}$"


@register
def pc_sequence_limit():
    r"""Limit of a Rational Sequence

    ``lim_{n->inf} (numerator)/(denominator)`` of equal-degree polynomials,
    equal to the ratio of leading coefficients (reduced).
    """
    degree = random.randint(1, 3)

    def _poly():
        terms = []
        lead = random.choice([i for i in range(-9, 10) if i != 0])
        terms.append((lead, degree))
        for exp in range(degree - 1, -1, -1):
            terms.append((random.randint(-9, 9), exp))
        return terms, lead

    num_terms, num_lead = _poly()
    den_terms, den_lead = _poly()
    frac = Fraction(num_lead, den_lead)
    numerator = _format_poly(num_terms, "n")
    denominator = _format_poly(den_terms, "n")
    problem = (
        f"Find $\\lim_{{n \\to \\infty}} \\frac{{{numerator}}}{{{denominator}}}$. "
        f"Express your answer as an integer or reduced fraction a/b."
    )
    if frac.denominator == 1:
        solution = f"${frac.numerator}$"
    else:
        solution = f"${frac.numerator}/{frac.denominator}$"
    return problem, solution


@register
def pc_vector_add(max_component=9):
    r"""Vector Operations (2D)

    Add, subtract, or scale two 2D vectors.
    """
    ux, uy = (random.randint(-max_component, max_component),
              random.randint(-max_component, max_component))
    vx, vy = (random.randint(-max_component, max_component),
              random.randint(-max_component, max_component))
    op = random.choice(["add", "sub", "scalar"])
    if op == "add":
        target = r"\vec{u} + \vec{v}"
        rx, ry = ux + vx, uy + vy
    elif op == "sub":
        target = r"\vec{u} - \vec{v}"
        rx, ry = ux - vx, uy - vy
    else:
        scalar = random.choice([i for i in range(-5, 6) if i not in (0, 1)])
        target = rf"{scalar}\vec{{u}}"
        rx, ry = scalar * ux, scalar * uy
    problem = (
        f"Let $\\vec{{u}} = \\langle {ux}, {uy} \\rangle$ and "
        f"$\\vec{{v}} = \\langle {vx}, {vy} \\rangle$. Compute ${target}$. "
        f"Give the resulting vector as (x, y)."
    )
    return problem, f"({rx}, {ry})"


@register
def pc_parametric_to_rectangular(max_bd=6):
    r"""Eliminate the Parameter

    Given ``x = a*t + b`` and ``y = c*t + d`` (a divides c), eliminate ``t`` to
    write ``y`` as a linear function of ``x``.
    """
    a = random.choice([i for i in range(-3, 4) if i != 0])
    quotient = random.choice([i for i in range(-4, 5) if i != 0])  # c / a
    c = a * quotient
    b = random.randint(-max_bd, max_bd)
    d = random.randint(-max_bd, max_bd)
    slope = c // a  # == quotient, integer
    intercept = d - slope * b

    if slope == 1:
        slope_str = "x"
    elif slope == -1:
        slope_str = "-x"
    else:
        slope_str = f"{slope}x"
    if intercept > 0:
        rhs = f"{slope_str} + {intercept}"
    elif intercept < 0:
        rhs = f"{slope_str} - {abs(intercept)}"
    else:
        rhs = slope_str

    b_str = f"+ {b}" if b >= 0 else f"- {abs(b)}"
    d_str = f"+ {d}" if d >= 0 else f"- {abs(d)}"
    problem = (
        f"Eliminate the parameter for $x = {a}t {b_str}$ and "
        f"$y = {c}t {d_str}$ to express $y$ as a linear function of $x$. "
        f"Write your answer in the form y = mx+b."
    )
    return problem, f"$y = {rhs}$"
