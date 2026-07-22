"""Solveki-local generators for Georgia "Geometry: Concepts & Connections".

Every generator here takes no required arguments, is decorated with
``@register``, and returns a ``(problem, solution)`` pair of LaTeX strings.
Answers are kept clean: integers, values rounded to at most three decimal
places, or reduced ``"a/b"`` fractions. Never seed ``random`` inside a
generator.
"""
import random
from math import cos, gcd, sin, tan

from ._registry import register
from ._format import num as _num


# Integer-sided right triangles, used where an exact answer is required.
_PYTHAG_TRIPLES = [
    (3, 4, 5),
    (5, 12, 13),
    (8, 15, 17),
    (7, 24, 25),
    (20, 21, 29),
    (9, 40, 41),
    (12, 35, 37),
]


def _signed_factor(var, val):
    """Render ``(var - val)`` with the sign folded in; ``val`` must be nonzero."""
    if val >= 0:
        return f"({var} - {val})"
    return f"({var} + {-val})"


def _reduce(num, den):
    """Return ``(num, den)`` reduced to lowest terms with a positive denominator."""
    if den < 0:
        num, den = -num, -den
    g = gcd(abs(num), den) or 1
    return num // g, den // g


@register
def geo_right_triangle_side(min_angle=15, max_angle=75, min_len=5, max_len=30):
    r"""Right Triangle: Solve for a Side with Trig

    Given one acute angle and one side of a right triangle, find another side
    using sine, cosine, or tangent (answer rounded to 3 decimal places).
    """
    ratios = {
        "opposite side": sin,
        "adjacent side": cos,
        "hypotenuse": lambda t: 1.0,
    }
    given, target = random.sample(list(ratios), 2)
    theta = random.randint(min_angle, max_angle)
    length = random.randint(min_len, max_len)

    rad = theta * 3.141592653589793 / 180
    r_given = ratios[given](rad)
    r_target = ratios[target](rad)
    answer = length * r_target / r_given

    problem = (
        f"In a right triangle, one acute angle measures ${theta}^\\circ$. "
        f"The {given} measures ${length}$. "
        f"Find the {target}, rounded to the nearest thousandth."
    )
    return problem, f"${_num(answer)}$"


@register
def geo_solve_right_triangle_pythag(max_scale=5):
    r"""Right Triangle: Pythagorean Theorem

    Using a Pythagorean triple (scaled), either find the hypotenuse from two
    legs or find the missing leg from a leg and the hypotenuse.
    """
    a, b, c = random.choice(_PYTHAG_TRIPLES)
    scale = random.randint(1, max_scale)
    a, b, c = a * scale, b * scale, c * scale

    if random.random() < 0.5:
        problem = (
            f"A right triangle has legs of length ${a}$ and ${b}$. "
            f"Find the length of the hypotenuse."
        )
        return problem, f"${c}$"

    problem = (
        f"A right triangle has a leg of length ${a}$ and a hypotenuse of "
        f"length ${c}$. Find the length of the other leg."
    )
    return problem, f"${b}$"


@register
def geo_circle_equation_from_center_radius(max_center=9, max_radius=12):
    r"""Circle: Equation from Center and Radius

    Given center ``(h, k)`` and radius ``r``, write the standard-form equation
    ``(x-h)^2 + (y-k)^2 = r^2``.
    """
    h = random.choice([n for n in range(-max_center, max_center + 1) if n != 0])
    k = random.choice([n for n in range(-max_center, max_center + 1) if n != 0])
    r = random.randint(1, max_radius)

    problem = (
        f"Write the equation of the circle with center $({h}, {k})$ and "
        f"radius ${r}$. Write your answer in the form (x-h)^2 + (y-k)^2 = c."
    )
    solution = (
        f"${_signed_factor('x', h)}^2 + {_signed_factor('y', k)}^2 = {r * r}$"
    )
    return problem, solution


@register
def geo_circle_center_radius_from_equation(max_center=9, max_radius=12):
    r"""Circle: Center and Radius from Equation

    Given a circle in standard form ``(x-h)^2 + (y-k)^2 = r^2``, state the
    center ``(h, k)`` and the radius ``r``.
    """
    h = random.choice([n for n in range(-max_center, max_center + 1) if n != 0])
    k = random.choice([n for n in range(-max_center, max_center + 1) if n != 0])
    r = random.randint(1, max_radius)

    problem = (
        f"Find the center and radius of the circle "
        f"${_signed_factor('x', h)}^2 + {_signed_factor('y', k)}^2 = {r * r}$. "
        f"Format your answer as such: center (1, 2), r=3."
    )
    return problem, f"center ({h}, {k}), r={r}"


@register
def geo_translate_point(max_coord=10):
    r"""Transformation: Translate a Point

    Translate a point by a vector and give the image point.
    """
    x, y = random.randint(-max_coord, max_coord), random.randint(-max_coord, max_coord)
    a, b = random.randint(-max_coord, max_coord), random.randint(-max_coord, max_coord)
    problem = (
        f"Translate the point $({x}, {y})$ by the vector "
        f"$\\langle {a}, {b} \\rangle$. Give the image point as (x, y)."
    )
    return problem, f"({x + a}, {y + b})"


@register
def geo_reflect_point(max_coord=10):
    r"""Transformation: Reflect a Point

    Reflect a point over the x-axis, y-axis, or the line ``y = x``.
    """
    x, y = random.randint(-max_coord, max_coord), random.randint(-max_coord, max_coord)
    line = random.choice(["x-axis", "y-axis", "line $y=x$"])
    if line == "x-axis":
        image = (x, -y)
    elif line == "y-axis":
        image = (-x, y)
    else:
        image = (y, x)
    problem = (
        f"Reflect the point $({x}, {y})$ over the {line}. "
        f"Give the image point as (x, y)."
    )
    return problem, f"({image[0]}, {image[1]})"


@register
def geo_rotate_point(max_coord=10):
    r"""Transformation: Rotate a Point

    Rotate a point 90, 180, or 270 degrees counterclockwise about the origin.
    """
    x, y = random.randint(-max_coord, max_coord), random.randint(-max_coord, max_coord)
    angle = random.choice([90, 180, 270])
    if angle == 90:
        image = (-y, x)
    elif angle == 180:
        image = (-x, -y)
    else:  # 270 CCW
        image = (y, -x)
    problem = (
        f"Rotate the point $({x}, {y})$ by ${angle}^\\circ$ counterclockwise "
        f"about the origin. Give the image point as (x, y)."
    )
    return problem, f"({image[0]}, {image[1]})"


@register
def geo_dilate_point(max_coord=6):
    r"""Transformation: Dilate a Point

    Dilate a point from the origin by an integer or simple fractional scale
    factor.
    """
    factor = random.choice(["2", "3", "4", "5", "1/2", "1/3"])
    if "/" in factor:
        num, den = (int(t) for t in factor.split("/"))
    else:
        num, den = int(factor), 1
    # Choose coordinates divisible by the denominator so the image is integer.
    x = den * random.randint(-max_coord, max_coord)
    y = den * random.randint(-max_coord, max_coord)
    nx, ny = x * num // den, y * num // den
    problem = (
        f"Dilate the point $({x}, {y})$ from the origin by a scale factor of "
        f"${factor}$. Give the image point as (x, y)."
    )
    return problem, f"({nx}, {ny})"


@register
def geo_inscribed_angle(min_half=10, max_half=89):
    r"""Circle: Inscribed Angle Theorem

    An inscribed angle is half of the central angle subtending the same arc;
    given one, find the other. The answer is the number of degrees only.
    """
    if random.random() < 0.5:
        central = 2 * random.randint(min_half, max_half)
        problem = (
            f"An inscribed angle and a central angle of a circle intercept the "
            f"same arc. The central angle measures ${central}^\\circ$. Find the "
            f"measure of the inscribed angle in degrees."
        )
        return problem, f"${central // 2}$"

    inscribed = random.randint(min_half, min(80, max_half))
    problem = (
        f"An inscribed angle and a central angle of a circle intercept the "
        f"same arc. The inscribed angle measures ${inscribed}^\\circ$. Find the "
        f"measure of the central angle in degrees."
    )
    return problem, f"${2 * inscribed}$"


@register
def geo_conditional_probability_table(max_count=40):
    r"""Probability: Conditional Probability from a Two-Way Table

    Given a 2x2 two-way frequency table, compute a conditional probability
    ``P(target | condition)`` as a reduced fraction.
    """
    # Rows A/B, columns X/Y.
    n_ax = random.randint(1, max_count)
    n_ay = random.randint(1, max_count)
    n_bx = random.randint(1, max_count)
    n_by = random.randint(1, max_count)

    condition = random.choice(["A", "B", "X", "Y"])
    if condition in ("A", "B"):
        target = random.choice(["X", "Y"])
    else:
        target = random.choice(["A", "B"])

    counts = {
        ("A", "X"): n_ax, ("A", "Y"): n_ay,
        ("B", "X"): n_bx, ("B", "Y"): n_by,
    }
    if condition in ("A", "B"):
        denom = counts[(condition, "X")] + counts[(condition, "Y")]
        numer = counts[(condition, target)]
    else:
        denom = counts[("A", condition)] + counts[("B", condition)]
        numer = counts[(target, condition)]
    num, den = _reduce(numer, denom)

    problem = (
        f"A two-way frequency table has these counts: A&X: {n_ax}, "
        f"A&Y: {n_ay}, B&X: {n_bx}, B&Y: {n_by}. "
        f"Find $P({target} \\mid {condition})$ as a reduced fraction."
    )
    return problem, f"${num}/{den}$"


@register
def geo_compound_probability():
    r"""Probability: Compound Probability of Independent Events

    For independent events A and B with given simple fractions, compute
    ``P(A and B)`` or ``P(A or B)`` as a reduced fraction.
    """
    simple = [(1, 2), (1, 3), (2, 3), (1, 4), (3, 4), (1, 5), (2, 5),
              (3, 5), (4, 5), (1, 6), (5, 6)]
    (a, b) = random.choice(simple)
    (c, d) = random.choice(simple)

    if random.random() < 0.5:
        # P(A and B) = P(A) * P(B)
        num, den = _reduce(a * c, b * d)
        connector = "and"
    else:
        # P(A or B) = P(A) + P(B) - P(A)P(B), common denominator b*d.
        num, den = _reduce(a * d + c * b - a * c, b * d)
        connector = "or"

    problem = (
        f"Events A and B are independent with $P(A) = {a}/{b}$ and "
        f"$P(B) = {c}/{d}$. Find $P(A \\text{{ {connector} }} B)$ as a reduced "
        f"fraction."
    )
    return problem, f"${num}/{den}$"


@register
def geo_expected_value():
    r"""Probability: Expected Value of a Discrete Distribution

    Compute the expected value of a small discrete distribution whose
    probabilities are stated as fractions (answer rounded to 3 decimal places).
    """
    k = random.choice([3, 4])
    den = random.choice([4, 5, 6, 8, 10, 12])
    # Random positive integer numerators summing to `den`.
    nums = [1] * k
    for _ in range(den - k):
        nums[random.randrange(k)] += 1
    values = random.sample(range(-5, 11), k)

    ev = sum(v * n for v, n in zip(values, nums)) / den

    parts = ", ".join(f"P(X={v})={n}/{den}" for v, n in zip(values, nums))
    problem = (
        f"A discrete random variable X has the distribution: {parts}. "
        f"Find the expected value E(X), rounded to the nearest thousandth."
    )
    return problem, f"${_num(ev)}$"
