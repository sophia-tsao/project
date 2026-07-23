"""Solveki-local overrides for ``mathgenerator`` angle/trig/conversion generators.

Group G3. Each generator's ``__name__`` deliberately matches a stock
``mathgenerator`` generator so ``_make_problem_for_topic`` (which resolves
``LOCAL_GENERATORS`` before the library) uses ours instead. The stock versions
are unusable here for the usual reasons: untypeable LaTeX answers
(``\\sec^{{2}}``, ``\\theta``), float noise like ``3.1999999999999993``, giant
random-float vectors, and answers that don't state a required rounding format
for a non-integer result.

Every generator is zero-required-arg, returns a ``(problem, solution)`` pair,
and produces a typeable solution (plain integers/decimals to 3dp, or a small
ASCII function string for the derivative).
"""
import math
import random
from fractions import Fraction

from ._registry import register
from ._format import num

_ROUND_HINT = "Give your answer as a decimal rounded to the nearest thousandth."
_RAD_HINT = "Give your answer in radians rounded to the nearest thousandth."


@register
def angle_regular_polygon():
    r"""Interior Angle of a Regular Polygon

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Find the measure of one interior angle of a regular polygon with $7$ sides... | 128.571 |

    Overrides the stock generator, which rounds to 2dp and states no format.
    Interior angle = ``(n - 2) * 180 / n`` degrees, often non-integer.
    """
    n = random.randint(3, 20)
    angle = (n - 2) * 180 / n
    problem = (
        f"Find the measure of one interior angle, in degrees, of a regular "
        f"polygon with ${n}$ sides. {_ROUND_HINT}"
    )
    return problem, num(angle)


def _vector_str(vec):
    """Render an integer vector as a typeable comma list, e.g. ``2, -3, 1``."""
    return ", ".join(str(v) for v in vec)


@register
def angle_btw_vectors():
    r"""Angle Between Two Vectors

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Find the angle between the vectors (2, -3) and (1, 4)... | 2.034 |

    Overrides the stock generator, which uses huge random floats and rounds to
    2dp. We use small integer vectors (2D or 3D) and compute
    ``arccos(dot / (|a| |b|))`` in radians. Vectors are guaranteed non-zero.
    """
    dim = random.choice([2, 3])

    def _nonzero_vec():
        while True:
            v = [random.randint(-6, 6) for _ in range(dim)]
            if any(c != 0 for c in v):
                return v

    a = _nonzero_vec()
    b = _nonzero_vec()
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    cos_theta = dot / (mag_a * mag_b)
    # Guard against tiny floating-point overshoot outside [-1, 1].
    cos_theta = max(-1.0, min(1.0, cos_theta))
    angle = math.acos(cos_theta)

    problem = (
        f"Find the angle between the vectors ({_vector_str(a)}) and "
        f"({_vector_str(b)}). {_RAD_HINT}"
    )
    return problem, num(angle)


@register
def degree_to_rad():
    r"""Convert Degrees to Radians

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Convert $68$ degrees to radians... | 1.187 |

    Overrides the stock generator (2dp, no stated format). Radians =
    ``degrees * pi / 180``.
    """
    degrees = random.randint(0, 360)
    radians = degrees * math.pi / 180
    problem = (
        f"Convert ${degrees}$ degrees to radians. {_ROUND_HINT}"
    )
    return problem, num(radians)


@register
def radian_to_deg():
    r"""Convert Radians to Degrees

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Convert $1.25$ radians to degrees... | 71.62 |

    Overrides the stock generator (2dp, no stated format). Degrees =
    ``radians * 180 / pi``. The input radian value is kept simple (a two-decimal
    value in [0, 6.28]).
    """
    # Simple two-decimal radian value so the problem statement is clean.
    radians = random.randint(0, 628) / 100
    degrees = radians * 180 / math.pi
    problem = (
        f"Convert ${num(radians)}$ radians to degrees. {_ROUND_HINT}"
    )
    return problem, num(degrees)


@register
def complex_to_polar():
    r"""Convert a Complex Number to Polar Form

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Write $3+4i$ in polar form (modulus and argument)... | 5, 0.927 |

    Overrides the stock generator, whose problem is malformed (stray
    ``\\theta``) and whose answer is a single number. Given ``a + bi`` we return
    the modulus ``r = sqrt(a^2 + b^2)`` and argument ``theta = atan2(b, a)`` in
    radians, formatted ``r, theta``.
    """
    a = random.randint(-12, 12)
    b = random.randint(-12, 12)
    # Avoid the origin, whose argument is undefined.
    while a == 0 and b == 0:
        a = random.randint(-12, 12)
        b = random.randint(-12, 12)

    modulus = math.sqrt(a * a + b * b)
    argument = math.atan2(b, a)

    # Render a + bi cleanly (handle sign of the imaginary part).
    if b >= 0:
        expr = f"{a}+{b}i"
    else:
        expr = f"{a}-{abs(b)}i"

    problem = (
        f"Write the complex number ${expr}$ in polar form. Give the modulus "
        f"and the argument (in radians), each rounded to the nearest "
        f"thousandth, formatted as 'r, theta' (e.g. 5, 0.927)."
    )
    solution = f"{num(modulus)}, {num(argument)}"
    return problem, solution


# Fixed set of basic functions whose derivative is typeable in pure ASCII.
# (function-as-written, derivative-as-ASCII).
_DERIVATIVES = [
    ("sin(x)", "cos(x)"),
    ("cos(x)", "-sin(x)"),
    ("tan(x)", "sec(x)^2"),
    ("sec(x)", "sec(x)*tan(x)"),
    ("csc(x)", "-csc(x)*cot(x)"),
    ("cot(x)", "-csc(x)^2"),
]


@register
def trig_differentiation():
    r"""Differentiate a Basic Trigonometric Function

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Differentiate $tan(x)$ with respect to $x$... | sec(x)^2 |

    Overrides the stock generator, whose answers use untypeable LaTeX
    (``\\sec^{{2}}``). We pick from a fixed set of basic functions and return the
    derivative as a canonical ASCII string.
    """
    func, derivative = random.choice(_DERIVATIVES)
    problem = (
        f"Differentiate ${func}$ with respect to $x$. Write your answer using "
        f"ASCII function notation, e.g. cos(x) or sec(x)^2."
    )
    return problem, derivative


@register
def fraction_to_decimal():
    r"""Convert a Fraction to a Decimal

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Convert the fraction $17/73$ to a decimal... | 0.233 |

    Overrides the stock generator (2dp, no stated format, ``\\div`` markup).
    Denominators are chosen so the result may not terminate.
    """
    numerator = random.randint(1, 99)
    denominator = random.randint(2, 99)
    value = numerator / denominator
    problem = (
        f"Convert the fraction ${numerator}/{denominator}$ to a decimal. "
        f"{_ROUND_HINT}"
    )
    return problem, num(value)


@register
def celsius_to_fahrenheit():
    r"""Convert Celsius to Fahrenheit

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Convert $-16$ degrees Celsius to degrees Fahrenheit... | 3.2 |

    Overrides the stock generator, which emits float noise like
    ``3.1999999999999993``. For an integer Celsius input the exact Fahrenheit
    value terminates at one decimal; :func:`num` renders it cleanly.
    """
    celsius = random.randint(-50, 50)
    fahrenheit = Fraction(celsius) * 9 / 5 + 32
    problem = (
        f"Convert ${celsius}$ degrees Celsius to degrees Fahrenheit. "
        f"{_ROUND_HINT}"
    )
    return problem, num(fahrenheit)
