"""Solveki-local arithmetic generators (Georgia grade 1-5 topics).

Each generator takes no required arguments and returns a ``(problem,
solution)`` tuple of two strings, with math wrapped in LaTeX ``$...$``. Answers
are kept clean: integers, short terminating decimals, or reduced fraction
strings like ``"3/4"``.
"""
import random
from decimal import Decimal
from math import gcd

from ._registry import register


def _reduce(num, den):
    """Return a reduced fraction string, or a plain integer string.

    ``num`` is assumed non-negative and ``den`` positive.
    """
    if num == 0:
        return "0"
    g = gcd(num, den)
    num //= g
    den //= g
    if den == 1:
        return str(num)
    return f"{num}/{den}"


def _fmt(value):
    """Format a Decimal/int as a plain decimal string with no trailing zeros."""
    d = Decimal(value).normalize()
    # Avoid exponent notation (e.g. '1E+2') that .normalize() can produce.
    return format(d, "f")


def _rand_decimal(max_int=99, dp_choices=(1, 2)):
    """Return a random non-negative decimal *string* with 1 or 2 dp."""
    dp = random.choice(dp_choices)
    whole = random.randint(0, max_int)
    frac = random.randint(0, 10 ** dp - 1)
    return f"{whole}.{frac:0{dp}d}"


def _ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


@register
def arith_place_value(min_length=3, max_length=5):
    r"""Place Value

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | What is the value of the digit 7 in the number 4738? | $700$ |
    """
    length = random.randint(min_length, max_length)
    # Distinct nonzero digits guarantee the chosen digit occurs exactly once
    # and the number has no leading zero.
    digits = random.sample(range(1, 10), length)
    number = int("".join(str(d) for d in digits))
    idx = random.randrange(length)
    digit = digits[idx]
    place = 10 ** (length - 1 - idx)
    value = digit * place
    problem = f"What is the value of the digit {digit} in the number {number}?"
    solution = f"${value}$"
    return problem, solution


@register
def arith_rounding(max_n=100000):
    r"""Rounding

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Round 4738 to the nearest hundred. | $4700$ |
    """
    place_name, p = random.choice(
        [("ten", 10), ("hundred", 100), ("thousand", 1000)]
    )
    n = random.randint(p, max_n)
    rounded = ((n + p // 2) // p) * p  # round half up
    problem = f"Round {n} to the nearest {place_name}."
    solution = f"${rounded}$"
    return problem, solution


@register
def arith_add_fractions(max_den=12):
    r"""Add Fractions

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Simplify $\frac{1}{2} + \frac{1}{3}$ | $5/6$ |
    """
    b = random.randint(2, max_den)
    d = random.randint(2, max_den)
    a = random.randint(1, b - 1)
    c = random.randint(1, d - 1)
    num = a * d + c * b
    den = b * d
    problem = (
        f"Simplify $\\frac{{{a}}}{{{b}}} + \\frac{{{c}}}{{{d}}}$. "
        f"Express your answer as a fraction in the form a/b, or an integer."
    )
    solution = f"${_reduce(num, den)}$"
    return problem, solution


@register
def arith_subtract_fractions(max_den=12):
    r"""Subtract Fractions

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Simplify $\frac{3}{4} - \frac{1}{2}$ | $1/4$ |
    """
    b = random.randint(2, max_den)
    d = random.randint(2, max_den)
    a = random.randint(1, b - 1)
    c = random.randint(1, d - 1)
    # Order so the result is non-negative.
    if a * d < c * b:
        a, b, c, d = c, d, a, b
    num = a * d - c * b
    den = b * d
    problem = (
        f"Simplify $\\frac{{{a}}}{{{b}}} - \\frac{{{c}}}{{{d}}}$. "
        f"Express your answer as a fraction in the form a/b, or an integer."
    )
    solution = f"${_reduce(num, den)}$"
    return problem, solution


@register
def arith_compare_decimals(max_int=99):
    r"""Compare Decimals

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Which is greater: $3.4$ or $3.45$? | $3.45$ |
    """
    x = _rand_decimal(max_int=max_int)
    y = _rand_decimal(max_int=max_int)
    while Decimal(x) == Decimal(y):
        y = _rand_decimal()
    larger = x if Decimal(x) > Decimal(y) else y
    problem = f"Which is greater: ${x}$ or ${y}$?"
    solution = f"${larger}$"
    return problem, solution


@register
def arith_add_decimals(max_int=99):
    r"""Add Decimals

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Calculate $12.5 + 3.25$ | $15.75$ |
    """
    x = _rand_decimal(max_int=max_int)
    y = _rand_decimal(max_int=max_int)
    res = Decimal(x) + Decimal(y)
    problem = f"Calculate ${x} + {y}$"
    solution = f"${_fmt(res)}$"
    return problem, solution


@register
def arith_subtract_decimals(max_int=99):
    r"""Subtract Decimals

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Calculate $12.5 - 3.25$ | $9.25$ |
    """
    x = _rand_decimal(max_int=max_int)
    y = _rand_decimal(max_int=max_int)
    if Decimal(x) < Decimal(y):
        x, y = y, x
    res = Decimal(x) - Decimal(y)
    problem = f"Calculate ${x} - {y}$"
    solution = f"${_fmt(res)}$"
    return problem, solution


@register
def arith_multiply_decimals(max_int=12):
    r"""Multiply Decimals

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Calculate $2.5 \times 3.2$ | $8$ |
    """
    x = _rand_decimal(max_int=max_int, dp_choices=(1,))
    y = _rand_decimal(max_int=max_int, dp_choices=(1,))
    res = Decimal(x) * Decimal(y)
    problem = f"Calculate ${x} \\times {y}$"
    solution = f"${_fmt(res)}$"
    return problem, solution


@register
def arith_order_of_operations(max_val=12):
    r"""Order of Operations

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Evaluate $(3 + 4) \times 2 - 5$ | $9$ |
    """
    a = random.randint(1, max_val)
    b = random.randint(1, max_val)
    c = random.randint(1, max_val)
    d = random.randint(1, max_val)
    templates = [
        f"({a} + {b}) \\times {c}",
        f"{a} \\times ({b} - {c})",
        f"{a} + {b} \\times {c} - {d}",
        f"({a} - {b}) \\times ({c} + {d})",
        f"{a} \\times {b} + {c}",
    ]
    expr = random.choice(templates)
    value = eval(expr.replace("\\times", "*"), {"__builtins__": {}}, {})
    problem = f"Evaluate ${expr}$"
    solution = f"${value}$"
    return problem, solution


@register
def arith_nth_multiple(max_n=20, max_base=12):
    r"""Nth Multiple

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | What is the 4th multiple of 7? | $28$ |
    """
    n = random.randint(2, max_n)
    base = random.randint(2, max_base)
    value = n * base
    problem = f"What is the {_ordinal(n)} multiple of {base}?"
    solution = f"${value}$"
    return problem, solution


@register
def arith_powers_of_ten(max_k=3):
    r"""Powers of Ten

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Calculate $34 \times 10^{2}$ | $3400$ |
    """
    k = random.randint(1, max_k)
    p = 10 ** k
    if random.random() < 0.5:
        n = random.randint(1, 999)
        res = Decimal(n) * Decimal(p)
        problem = f"Calculate ${n} \\times 10^{{{k}}}$"
    else:
        n = random.randint(1, 9999)
        res = Decimal(n) / Decimal(p)
        problem = f"Calculate ${n} \\div 10^{{{k}}}$"
    solution = f"${_fmt(res)}$"
    return problem, solution


# Conversion factors, each unit expressed in the system's smallest unit.
_LENGTH_SYSTEMS = {
    "metric": {"km": 100000, "m": 100, "cm": 1},
    "customary": {"yd": 36, "ft": 12, "in": 1},
}


@register
def arith_length_conversion(max_value=20):
    r"""Length Conversion

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Convert 5 km to m. | $5000$ |
    """
    units = random.choice(list(_LENGTH_SYSTEMS.values()))
    from_unit, to_unit = random.sample(list(units), 2)
    f_from = units[from_unit]
    f_to = units[to_unit]
    if f_from >= f_to:
        value = random.randint(1, max_value)
    else:
        # Smaller -> larger unit: pick a value that divides cleanly.
        step = f_to // f_from
        value = random.randint(1, max_value) * step
    result = value * f_from // f_to
    problem = f"Convert {value} {from_unit} to {to_unit}."
    solution = f"${result}$"
    return problem, solution


@register
def arith_elapsed_time(max_duration=600):
    r"""Elapsed Time

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | A train departs at 12:15 and travels for 140 minutes. ... | $14:35$ |
    """
    h = random.randint(0, 23)
    m = random.randint(0, 59)
    dur = random.randint(1, max_duration)
    total = (h * 60 + m + dur) % (24 * 60)
    eh, em = divmod(total, 60)
    start = f"{h}:{m:02d}"
    problem = (
        f"A train departs at {start} and travels for {dur} minutes. "
        f"Using a 24-hour clock, at what time does it arrive?"
    )
    solution = f"${eh}:{em:02d}$"
    return problem, solution


@register
def arith_money(max_cents=5000):
    r"""Money

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Find the result in dollars: $9.25 + 3.50$ | $12.75$ |
    """
    op = random.choice(["+", "-"])
    a = (Decimal(random.randint(1, max_cents)) / 100).quantize(Decimal("0.01"))
    b = (Decimal(random.randint(1, max_cents)) / 100).quantize(Decimal("0.01"))
    if op == "-" and a < b:
        a, b = b, a
    res = (a + b if op == "+" else a - b).quantize(Decimal("0.01"))
    problem = f"Find the result in dollars: ${a} {op} {b}$"
    solution = f"${res}$"
    return problem, solution


@register
def arith_area_of_rectangle(max_side=50):
    r"""Area of a Rectangle

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | A rectangle has length 7 units and width 4 units. ... | $28$ |
    """
    length = random.randint(1, max_side)
    width = random.randint(1, max_side)
    area = length * width
    problem = (
        f"A rectangle has length {length} units and width {width} units. "
        f"What is its area in square units?"
    )
    solution = f"${area}$"
    return problem, solution
