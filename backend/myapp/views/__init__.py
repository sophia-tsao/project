"""HTTP views for myapp, split by concern.

This package used to be a single ``views.py``. It's kept importable as
``myapp.views`` with the same public surface, so ``urls.py`` and the test
suite need no changes. New code should import from the specific submodule
(e.g. ``from myapp.views.deck import _build_deck``); the re-exports below
exist for backwards compatibility.
"""

# Re-exported so tests can patch ``myapp.views.mathgenerator`` and
# ``myapp.views.google_id_token`` (mock.patch resolves the module object here,
# and the submodules reference the same object).
import mathgenerator  # noqa: F401
from google.oauth2 import id_token as google_id_token  # noqa: F401

from .auth import (
    me,
    google_login,
    logout_view,
    delete_account,
)
from .courses import (
    view_courses,
    view_course_topics,
    toggle_topic,
    set_course_topics_selected,
)
from .problems import generate_problem, _make_problem
from .settings import settings_view
from .deck import get_deck, advance_deck

__all__ = [
    "me",
    "google_login",
    "logout_view",
    "delete_account",
    "view_courses",
    "view_course_topics",
    "toggle_topic",
    "set_course_topics_selected",
    "generate_problem",
    "settings_view",
    "get_deck",
    "advance_deck",
]
