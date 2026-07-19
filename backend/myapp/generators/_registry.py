"""Registry for Solveki-local problem generators.

Each generator is a zero-required-arg callable returning a ``(problem,
solution)`` tuple — the same contract as a ``mathgenerator`` generator, so the
two are interchangeable in ``_make_problem``. Decorate a generator with
``@register`` and it becomes resolvable by its function name.
"""

# name -> generator callable. Populated by @register at import time.
LOCAL_GENERATORS = {}


def register(fn):
    """Register `fn` under its own name. Raises on a duplicate name."""
    name = fn.__name__
    if name in LOCAL_GENERATORS:
        raise ValueError(f"Duplicate local generator name: {name!r}")
    LOCAL_GENERATORS[name] = fn
    return fn
