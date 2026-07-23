"""Solveki-local overrides for ``mathgenerator`` circle & coordinate geometry.

Every generator here is named to *exactly* match a stock ``mathgenerator``
generator so it overrides the library version (``_make_problem_for_topic``
resolves ``LOCAL_GENERATORS`` before the library). The library versions are
unusable in Solveki's exact-match answer box for a mix of reasons:

* ``distance_two_points`` answers with ``\\sqrt{...}`` (untypeable).
* ``euclidian_norm`` builds a vector of random floats (untypeable, unparseable).
* ``equation_of_line_from_two_points`` is arithmetically *wrong* — it returns
  strings like ``9y = 22x + 184`` instead of proper slope-intercept form.
* The circle/sector/midpoint generators are close but we restate the required
  answer format explicitly (rounding, ``(x, y)``) so a student knows what to
  type, and we keep every input a small integer suitable for review.

Each generator returns typeable answers only: integers, decimals rounded to the
nearest thousandth via :func:`num`, ``a/b`` fractions, or ``(x, y)`` pairs.
``random`` is used directly and never seeded here.
"""
import math
import random
from fractions import Fraction

from ._registry import register
from ._format import num, pair, frac_from

_ROUND_HINT = "Round your answer to the nearest thousandth."


def _coord(lo, hi):
    """A random integer coordinate in ``[lo, hi]``."""
    return random.randint(lo, hi)


@register
def area_of_circle(min_radius=1, max_radius=20):
    r"""Area of a Circle

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Find the area of a circle with radius $8$. ... | 201.062 |

    Overrides the stock ``area_of_circle``. Area $= \pi r^2$; answer is a
    decimal, so the problem states the rounding the answer box expects.
    """
    r = random.randint(min_radius, max_radius)
    area = math.pi * r * r
    problem = (
        f"Find the area of a circle with radius ${r}$. {_ROUND_HINT}"
    )
    return problem, num(area)


@register
def area_of_circle_given_center_and_point(coord_min=-10, coord_max=10):
    r"""Area of a Circle Given Center and a Point On It

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | ...center $(2, -4)$ passing through $(12, -4)$... | 314.159 |

    Overrides the stock version. The radius is the distance from the center to
    the given point, then area $= \pi r^2$. Both points are integers (the point
    is forced distinct from the center so the radius is positive).
    """
    cx = _coord(coord_min, coord_max)
    cy = _coord(coord_min, coord_max)
    while True:
        px = _coord(coord_min, coord_max)
        py = _coord(coord_min, coord_max)
        if (px, py) != (cx, cy):
            break
    r2 = (px - cx) ** 2 + (py - cy) ** 2
    area = math.pi * r2
    problem = (
        f"Find the area of the circle with center $({cx}, {cy})$ that passes "
        f"through the point $({px}, {py})$. {_ROUND_HINT}"
    )
    return problem, num(area)


@register
def circumference(min_radius=1, max_radius=20):
    r"""Circumference of a Circle

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Find the circumference of a circle with radius $8$. ... | 50.265 |

    Overrides the stock version. Circumference $= 2\pi r$; decimal answer, so
    the problem states the rounding.
    """
    r = random.randint(min_radius, max_radius)
    circ = 2 * math.pi * r
    problem = (
        f"Find the circumference of a circle with radius ${r}$. {_ROUND_HINT}"
    )
    return problem, num(circ)


@register
def sector_area(min_radius=1, max_radius=20, min_angle=1, max_angle=359):
    r"""Area of a Sector

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | ...radius $9$ and central angle $292$ degrees... | 206.428 |

    Overrides the stock version. Sector area $= (\theta/360)\,\pi r^2$ for an
    angle in degrees; decimal answer, so the problem states the rounding.
    """
    r = random.randint(min_radius, max_radius)
    theta = random.randint(min_angle, max_angle)
    area = (theta / 360) * math.pi * r * r
    problem = (
        f"Find the area of a sector with radius ${r}$ and central angle "
        f"${theta}$ degrees. {_ROUND_HINT}"
    )
    return problem, num(area)


@register
def distance_two_points(coord_min=-15, coord_max=15):
    r"""Distance Between Two Points

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Find the distance between $(-12, 16)$ and $(-16, -4)$. ... | 20.396 |

    Overrides the stock version, which answers with an untypeable
    ``\sqrt{...}``. We return the distance as a decimal rounded to the nearest
    thousandth and state the rounding.
    """
    x1 = _coord(coord_min, coord_max)
    y1 = _coord(coord_min, coord_max)
    x2 = _coord(coord_min, coord_max)
    y2 = _coord(coord_min, coord_max)
    dist = math.hypot(x2 - x1, y2 - y1)
    problem = (
        f"Find the distance between the points $({x1}, {y1})$ and "
        f"$({x2}, {y2})$. {_ROUND_HINT}"
    )
    return problem, num(dist)


@register
def midpoint_of_two_points(coord_min=-15, coord_max=15):
    r"""Midpoint of Two Points

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | The midpoint of $(-13, 11)$ and $(8, 10)$... | (-2.5, 10.5) |

    Overrides the stock version. Midpoint $= ((x_1+x_2)/2, (y_1+y_2)/2)$; each
    component may be a half-integer, so the problem states the ``(x, y)`` format
    and each component is rendered via :func:`num`.
    """
    x1 = _coord(coord_min, coord_max)
    y1 = _coord(coord_min, coord_max)
    x2 = _coord(coord_min, coord_max)
    y2 = _coord(coord_min, coord_max)
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    problem = (
        f"Find the midpoint of the points $({x1}, {y1})$ and $({x2}, {y2})$. "
        f"Format your answer as (x, y)."
    )
    return problem, pair(mx, my)


@register
def euclidian_norm(min_dim=2, max_dim=4, comp_min=-10, comp_max=10):
    r"""Euclidian (L2) Norm of a Vector

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Find the L2 norm of the vector $(3, -4)$. ... | 5 |

    Overrides the stock version, which uses a long vector of random floats. We
    use a short small-integer vector and return the L2 norm as a decimal
    rounded to the nearest thousandth (an integer when the norm is whole).
    """
    dim = random.randint(min_dim, max_dim)
    # At least one nonzero component so the norm is positive and meaningful.
    while True:
        components = [random.randint(comp_min, comp_max) for _ in range(dim)]
        if any(components):
            break
    norm = math.sqrt(sum(c * c for c in components))
    vector = ", ".join(str(c) for c in components)
    problem = (
        f"Find the Euclidean norm (L2 norm) of the vector $({vector})$. "
        f"{_ROUND_HINT}"
    )
    return problem, num(norm)


def _line_solution(m, b):
    """Render ``y = mx + b`` typeably from ``Fraction`` slope ``m`` and
    intercept ``b`` (m != 0). Coefficients render as integers or ``a/b``."""
    if m == 1:
        slope_term = "x"
    elif m == -1:
        slope_term = "-x"
    else:
        slope_term = f"{frac_from(m)}x"
    out = f"y = {slope_term}"
    if b > 0:
        out += f" + {frac_from(b)}"
    elif b < 0:
        out += f" - {frac_from(-b)}"
    return out


@register
def equation_of_line_from_two_points(coord_min=-10, coord_max=10):
    r"""Equation of a Line From Two Points

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | ...line through $(0, 5)$ and $(1, 8)$... | y = 3x + 5 |
    | ...line through $(0, 1)$ and $(3, 3)$... | y = 2/3x + 1 |

    Overrides the stock version, which is arithmetically WRONG (it returns
    strings like ``9y = 22x + 184`` rather than slope-intercept form). We
    compute slope $m=(y_2-y_1)/(x_2-x_1)$ and intercept $b=y_1-m x_1$ exactly
    with fractions, then render a canonical ``y = mx + b`` (slope and intercept
    as integers or typeable ``a/b`` fractions). ``x_2 != x_1`` and ``y_2 != y_1``
    are enforced so the line is neither vertical nor horizontal.
    """
    while True:
        x1 = _coord(coord_min, coord_max)
        y1 = _coord(coord_min, coord_max)
        x2 = _coord(coord_min, coord_max)
        y2 = _coord(coord_min, coord_max)
        if x2 != x1 and y2 != y1:
            break
    m = Fraction(y2 - y1, x2 - x1)
    b = Fraction(y1) - m * x1
    problem = (
        f"Find the equation of the line through the points $({x1}, {y1})$ and "
        f"$({x2}, {y2})$. Give your answer in slope-intercept form y = mx+b."
    )
    return problem, _line_solution(m, b)
