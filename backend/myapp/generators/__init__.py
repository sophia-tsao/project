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

# Local overrides of broken stock ``mathgenerator`` generators. Each module
# registers generators whose names match a library generator, so they take
# precedence in ``_make_problem_for_topic`` (which resolves LOCAL_GENERATORS
# first). They fix untypeable answers, missing format/rounding instructions,
# broken rendering, and outright wrong answers in the library versions.
from . import (  # noqa: F401,E402
    lib_algebra_extra_gen,
    lib_angles_gen,
    lib_finance_gen,
    lib_fractions_gen,
    lib_geometry_gen,
    lib_powers_gen,
    lib_seqstats_gen,
    lib_solids_gen,
)

__all__ = ["LOCAL_GENERATORS", "register"]
