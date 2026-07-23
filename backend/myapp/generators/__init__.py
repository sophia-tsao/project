"""Solveki-local problem generators.

These extend the stock ``mathgenerator`` library with generators we maintain
ourselves. ``_make_problem`` resolves a name here first, then falls back to
``mathgenerator``.

To add a generator: write a function returning ``(problem, solution)`` in the
appropriate category module and decorate it with ``@register``. Then import
that module below so its registration runs. The contract test in
``test_generators.py`` automatically covers every registered generator.
"""
from ._registry import LOCAL_GENERATORS, register  # noqa: F401

# Import each category module for its @register side effects. Add new modules
# here as you create them (e.g. calculus, geometry).
from . import (  # noqa: F401,E402
    algebra,
    algebra1,
    algebra2,
    arithmetic,
    calculus,
    geometry,
    geometry_hs,
    prealgebra,
    precalculus,
    sets_gen,
    statistics_gen,
)

__all__ = ["LOCAL_GENERATORS", "register"]
