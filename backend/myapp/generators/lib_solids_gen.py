"""Solveki-local overrides for broken ``mathgenerator`` solids & roots generators.

Each generator here is named to *exactly* match a stock ``mathgenerator``
generator so ``_make_problem_for_topic`` (which resolves ``LOCAL_GENERATORS``
before the library) overrides the broken library version.

The library versions in this group share two families of defects:

* **Silent, wrong-precision rounding** — several pre-round to 2 decimals with no
  instruction (``pythagorean_theorem`` emits ``9.43`` when the true 3dp value is
  ``9.434``; ``area_of_triangle`` and ``curved_surface_area_cylinder`` likewise),
  so a student who rounds correctly to the thousandth is marked wrong. Others
  emit full unrounded floats (``314.1592653589793``) that no one could type.
* **Malformed / untypeable problem text** — ``area_of_triangle`` renders sides as
  ``$5, 19 16 = $`` (missing comma, dangling ``=``) and can emit degenerate
  triangles; ``cube_root`` uses ``\\sqrt[3]{...}``.

Every override computes at full precision, formats the number with :func:`num`
(round to the nearest thousandth, drop a trailing ``.0``), and — whenever the
answer is not always a plain integer — states the required rounding in the
problem text. Units match the library (``m^2`` / ``m^3``).
"""
import math
import random

from ._registry import register
from ._format import num

_ROUND_HINT = "Round your answer to the nearest thousandth."


@register
def surface_area_sphere(min_r=2, max_r=20):
    r"""Surface Area of a Sphere

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Surface area of a sphere with radius $= 5 m$. Round... | $314.159 m^2$ |

    Overrides the stock generator, which emits an untypeable full-precision
    float (e.g. ``314.1592653589793``) with no rounding instruction.
    """
    r = random.randint(min_r, max_r)
    area = 4 * math.pi * r ** 2
    problem = (
        f"Find the surface area of a sphere with radius $= {r} m$. {_ROUND_HINT}"
    )
    return problem, f"${num(area)} m^2$"


@register
def volume_sphere(min_r=2, max_r=20):
    r"""Volume of a Sphere

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Volume of a sphere with radius $9 m$. Round... | $3053.628 m^3$ |

    Overrides the stock generator, which emits an untypeable full-precision
    float with no rounding instruction.
    """
    r = random.randint(min_r, max_r)
    volume = (4 / 3) * math.pi * r ** 3
    problem = (
        f"Find the volume of a sphere with radius $= {r} m$. {_ROUND_HINT}"
    )
    return problem, f"${num(volume)} m^3$"


@register
def volume_hemisphere(min_r=2, max_r=20):
    r"""Volume of a Hemisphere

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Volume of a hemisphere with radius $9 m$. Round... | $1526.814 m^3$ |

    Overrides the stock generator, which pre-rounds to 3dp without instruction.
    """
    r = random.randint(min_r, max_r)
    volume = (2 / 3) * math.pi * r ** 3
    problem = (
        f"Find the volume of a hemisphere with radius $= {r} m$. {_ROUND_HINT}"
    )
    return problem, f"${num(volume)} m^3$"


@register
def volume_pyramid(min_dim=2, max_dim=20):
    r"""Volume of a Pyramid

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Volume of a pyramid with base area $= 45 m^2$ and height $= 8 m$. | $120 m^3$ |

    Overrides the stock generator, which emits trailing-``.0`` answers (``220.0``)
    and long unrounded decimals (``1551.6666666666667``) with no instruction.
    ``num`` drops the ``.0`` and rounds long decimals to the thousandth.
    """
    base_area = random.randint(min_dim, max_dim) * random.randint(min_dim, max_dim)
    height = random.randint(min_dim, max_dim)
    volume = (1 / 3) * base_area * height
    problem = (
        f"Find the volume of a pyramid with base area $= {base_area} m^2$ and "
        f"height $= {height} m$. {_ROUND_HINT}"
    )
    return problem, f"${num(volume)} m^3$"


@register
def curved_surface_area_cylinder(min_r=2, max_r=20, min_h=2, max_h=20):
    r"""Curved Surface Area of a Cylinder

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Curved surface area of a cylinder with radius $9 m$, height $73 m$. | $4128.052 m^2$ |

    Overrides the stock generator, which silently pre-rounds to 2dp (``4128.05``)
    with no instruction, marking a correct 3dp answer wrong.
    """
    r = random.randint(min_r, max_r)
    h = random.randint(min_h, max_h)
    area = 2 * math.pi * r * h
    problem = (
        f"Find the curved surface area of a cylinder with radius $= {r} m$ and "
        f"height $= {h} m$. {_ROUND_HINT}"
    )
    return problem, f"${num(area)} m^2$"


@register
def cube_root(min_root=1, max_root=20):
    r"""Cube Root

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | What is the cube root of $2744$? | $14$ |

    Overrides the stock generator, whose problem uses ``\sqrt[3]{...}`` and
    pre-rounds to 2dp with no instruction. We pick a *perfect cube* so the cube
    root is always a clean integer — no rounding needed, no instruction required.
    """
    root = random.randint(min_root, max_root)
    n = root ** 3
    problem = f"What is the cube root of ${n}$?"
    return problem, f"${num(root)}$"


@register
def area_of_triangle(min_side=3, max_side=20):
    r"""Area of a Triangle (Heron's Formula)

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Area of a triangle with side lengths $6$, $7$, and $9$. Round... | $20.976 m^2$ |

    Overrides the stock generator, which renders sides poorly (``$5, 19 16 = $``),
    can emit degenerate (non-triangle) side sets, and pre-rounds to 2dp with no
    instruction. We resample until the triangle inequality is *strictly*
    satisfied, then apply Heron's formula at full precision.
    """
    while True:
        a = random.randint(min_side, max_side)
        b = random.randint(min_side, max_side)
        c = random.randint(min_side, max_side)
        # Strict triangle inequality: every side less than the sum of the others.
        if a + b > c and a + c > b and b + c > a:
            break
    s = (a + b + c) / 2
    area = math.sqrt(s * (s - a) * (s - b) * (s - c))
    problem = (
        f"Find the area of a triangle with side lengths $= {a} m$, $= {b} m$, "
        f"and $= {c} m$. {_ROUND_HINT}"
    )
    return problem, f"${num(area)} m^2$"


@register
def pythagorean_theorem(min_leg=2, max_leg=15):
    r"""Pythagorean Theorem (Hypotenuse)

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Hypotenuse of a right triangle with legs $5$ and $19$. Round... | $19.647 |

    Overrides the stock generator, which pre-rounds to 2dp (``19.65``) with no
    instruction, so a student who rounds correctly to the thousandth
    (``19.647``) is marked wrong. We compute at full precision and round to 3dp.
    """
    a = random.randint(min_leg, max_leg)
    b = random.randint(min_leg, max_leg)
    hypotenuse = math.sqrt(a ** 2 + b ** 2)
    problem = (
        f"What is the length of the hypotenuse of a right triangle whose legs "
        f"have lengths $= {a}$ and $= {b}$? {_ROUND_HINT}"
    )
    return problem, f"${num(hypotenuse)}$"
