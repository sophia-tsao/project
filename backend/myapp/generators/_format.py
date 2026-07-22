"""Shared formatters for typeable generator solutions.

Every Solveki-local generator returns a solution string the student types back
on their keyboard, so answers must avoid LaTeX that can't be typed: no
``\\frac``, ``\\sqrt``, ``\\langle``, ``\\geq``, matrices, or set notation.
These helpers are the single source of truth for rendering the typeable forms
(plain integers, decimals, ``a/b`` fractions, and ``(x, y)`` pairs).
"""
from fractions import Fraction


def num(value, places=3):
    """Format a number cleanly and typeably.

    Rounds to ``places`` decimals, then drops a trailing ``.0`` so an integral
    result reads as ``8`` rather than ``8.0``. Normalises ``-0`` to ``0``.
    """
    rounded = round(float(value), places)
    if rounded == int(rounded):
        return str(int(rounded))
    # ``str`` on a rounded float is already at most `places` decimals; strip a
    # trailing zero pair like 2.50 -> 2.5 defensively.
    text = f"{rounded:.{places}f}".rstrip("0").rstrip(".")
    return text if text else "0"


def frac(numerator, denominator):
    """Render a fraction typeably: ``'n'`` when whole, else reduced ``'p/q'``."""
    fr = Fraction(numerator, denominator)
    if fr.denominator == 1:
        return str(fr.numerator)
    return f"{fr.numerator}/{fr.denominator}"


def frac_from(value):
    """Render a ``Fraction`` (or int) typeably as ``'n'`` or reduced ``'p/q'``."""
    fr = Fraction(value)
    if fr.denominator == 1:
        return str(fr.numerator)
    return f"{fr.numerator}/{fr.denominator}"


def pair(x, y):
    """Render an ordered pair ``(x, y)`` with each component via :func:`num`."""
    return f"({num(x)}, {num(y)})"
