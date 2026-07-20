# Solveki — Design

Solveki is a math-practice web app. A Django JSON API backend serves generated
math problems to a React single-page frontend. Users sign in with Google, pick
course topics, and work through a daily deck of problems. A Bruno collection
documents the API for manual QA.

## Repo layout

```
solveki/
├── backend/          Django project — JSON API, problem generators, SQLite DB
│   ├── config/       project package (settings, urls, asgi/wsgi)
│   ├── myapp/        the single app (models, views, generators, tests, commands)
│   └── frontend/     React 19 SPA built with Vite
├── bruno/            Bruno API client collection (one request per endpoint)
├── README.md
└── .github/          CI
```

## Backend (Django 6.0.4)

Plain Django with function-based views returning `JsonResponse` — no DRF.
Dependencies (`backend/pyproject.toml`): `django==6.0.4`,
`django-cors-headers`, `google-auth`, `mathgenerator==1.5.0`. Python ≥ 3.11,
SQLite.

### Authentication

Google ID tokens are verified server-side
(`google.oauth2.id_token.verify_oauth2_token`) and mapped to a Django session
login. CORS is configured for the Vite dev origin (`http://localhost:5173`)
with `CORS_ALLOW_CREDENTIALS = True` so the SPA can send the session cookie
cross-origin. `settings.py` uses a small dependency-free `_load_dotenv()` to
read `backend/.env`.

### Data model (`backend/myapp/models.py`)

- **Course** — `course_name`, `grade_level`.
- **Topic** — `topic_name`, FK `course`, and `generator_name` (the string that
  maps a topic to a generator callable). This field is the linchpin of the
  generator system.
- **UserTopicSelection** — per-user selection row (user, topic), unique
  together; row existence means "selected".
- **Settings** — one-to-one per user; `language`, `questions_per_day`.
- **DailyDeck** — per user + date; `problems` (JSON list of `{problem,
  solution}`) and `current_index`.

### Endpoints (`backend/myapp/urls.py`)

| Method | Path | View |
| --- | --- | --- |
| GET | `auth/me/` | `me` |
| POST | `auth/google/` | `google_login` |
| POST | `auth/logout/` | `logout_view` |
| DELETE | `auth/delete/` | `delete_account` |
| GET | `problem/` | `generate_problem` |
| GET | `deck/` | `get_deck` |
| POST | `deck/advance/` | `advance_deck` |
| GET/PATCH | `settings/` | `settings_view` |
| GET | `courses/` | `view_courses` |
| GET | `courses/<id>/topics` | `view_course_topics` |
| PATCH | `courses/<id>/select` | `set_course_topics_selected` |
| PATCH | `topics/<id>/select` | `toggle_topic` |

Deck logic (`_get_or_create_today_deck`, `_build_deck`, `_deck_payload`) builds
a per-day deck of `questions_per_day` problems and discards stale prior-day
decks.

## Frontend (React 19 + Vite 8)

Located at `backend/frontend/`. Uses KaTeX for math rendering and oxlint for
linting. `App.jsx` is a top-level router-by-state (`math`, `courses`,
`settings` pages; `LoginPage` when unauthenticated). Practice UI lives in
`MathProblem.jsx` / `MathProblemDisplay.jsx` / `MathProblemResponse.jsx`
(problem rendering, answer box, two-attempt flow); course selection in
`CourseList.jsx` / `CourseBar.jsx`; auth helpers in `auth.js`.

## The math generator system

This is the core design decision, reshaped by commit *"De-vendor
mathgenerator, add generator contract tests"*.

### Background: why de-vendored

The repo previously vendored a **fork** of `mathgenerator` under
`backend/mathgenerator/`. The fork added three custom generators not present in
PyPI's `mathgenerator==1.5.0`: `vertex_form`, `angle_sum`, and
`aroc_over_interval`. Maintaining a whole forked library to carry three
functions is expensive. The commit deleted the vendored copy, switched to the
pip dependency, and preserved just the three custom generators in a new
first-party package, `backend/myapp/generators/`.

### The generator contract

A generator is a **zero-required-arg callable that returns `(problem,
solution)`**. This is deliberately identical to a `mathgenerator` generator, so
the app's own generators and library generators are interchangeable at the call
site.

### Importing the library

The pip package is imported directly where problems are made:

```python
import mathgenerator
```

Its generators are resolved by name via `getattr(mathgenerator, name)`.

### The local registry (`backend/myapp/generators/_registry.py`)

Local generators register themselves with a decorator at import time:

```python
# name -> generator callable. Populated by @register at import time.
LOCAL_GENERATORS = {}

def register(fn):
    """Register `fn` under its own name. Raises on a duplicate name."""
    name = fn.__name__
    if name in LOCAL_GENERATORS:
        raise ValueError(f"Duplicate local generator name: {name!r}")
    LOCAL_GENERATORS[name] = fn
    return fn
```

### Package init — the import side-effect trick (`generators/__init__.py`)

Registration only happens when a category module is imported, so the package
`__init__.py` imports each category module for its side effects:

```python
from ._registry import LOCAL_GENERATORS, register  # noqa: F401

# Import each category module for its @register side effects. Add new modules
# here as you create them (e.g. calculus, geometry).
from . import algebra, geometry  # noqa: F401,E402

__all__ = ["LOCAL_GENERATORS", "register"]
```

### An example generator (`generators/algebra.py`)

```python
from ._registry import register

@register
def vertex_form(min_val=-10, max_val=10, min_a=-5, max_a=5):
    r"""Vertex of a Quadratic in Vertex Form ..."""
    a = random.choice([i for i in range(min_a, max_a + 1) if i != 0])
    h = random.randint(min_val, max_val)
    k = random.randint(min_val, max_val)
    h_str = f"x{'+' if -h >= 0 else '-'}{abs(h)}" if h != 0 else "x"
    a_str = "" if a == 1 else ("-" if a == -1 else str(a))
    problem = f"Find the coordinates of the vertex of $y={a_str}({h_str})^2{'+' if k >= 0 else '-'}{abs(k)}$"
    solution = f"$({h}, {k})$"
    return problem, solution
```

Generators may declare default kwargs but must be callable with zero args.
`algebra.py` holds `vertex_form` and `aroc_over_interval`; `geometry.py` holds
`angle_sum`.

### Resolving a name to a generator (`views.py`, `_make_problem`)

The local registry and the library are fused here — local generators win, then
the library is the fallback:

```python
from .generators import LOCAL_GENERATORS
import mathgenerator

# Prefer our own generators, then fall back to the mathgenerator library.
generator = LOCAL_GENERATORS.get(name) or getattr(mathgenerator, name, None)
if generator is None:
    # Unknown name (renamed/removed by a library upgrade) -> no problem,
    # rather than 500-ing the student.
    return None
problem, solution = generator()
```

`_make_problem` picks a random `generator_name` among the user's selected
topics, resolves it, invokes it, then normalizes the solution (strips LaTeX
`$`, rounds decimals, appends a rounding instruction when rounding changes the
value).

### Wiring topics to generators (`management/commands/seed_topics.py`)

`Topic.generator_name` is the only link. The `TOPICS` seed list maps each topic
to a generator name — the three custom locals plus ~60 stock library names:

```python
("Average Rate of Change over Interval", "aroc_over_interval"),
("Angle Sum", "angle_sum"),
("Vertex of a Quadratic in Vertex Form", "vertex_form"),
("Addition", "addition"),          # stock mathgenerator
("Area of Triangle", "area_of_triangle"),
```

### Contract tests (`myapp/tests/test_generators.py`)

- **`SeedGeneratorContractTests`**
  - `test_names_exist` — every seeded `generator_name` is in
    `mathgenerator.get_gen_list()` ∪ `LOCAL_GENERATORS`. Guards against library
    upgrades or typos silently breaking a topic.
  - `test_names_produce_output` — resolves each name the way `_make_problem`
    does and calls it (retries up to 5 times under a fixed seed so a degenerate
    random draw can't flake CI).
- **`LocalGeneratorTests`** (stronger checks for owned code)
  - `test_all_local_generators_return_well_formed_pairs` — non-empty string
    problem and solution.
  - `test_vertex_form_is_deterministic_under_seed` — stable output under a
    fixed seed.

## How generators are exposed via the API

There is **no endpoint that lists generators**. They are exposed indirectly
through topics: `view_courses` / `view_course_topics` return topics (including
`generator_name`) with per-user selection state; the frontend lets the user
select topics; `generate_problem` and the deck endpoints call `_make_problem`,
which randomly chooses among the selected topics' generators and returns
`{problem, solution}`. Unknown names degrade gracefully to "no problem."

## Adding a new custom generator

1. Write `@register def foo(): return problem, solution` in the appropriate
   category module under `backend/myapp/generators/` (or add a new category
   module).
2. If it's a new module, import it in `generators/__init__.py` so its
   `@register` runs.
3. Add a `("Some Topic", "foo")` entry to `TOPICS` in `seed_topics.py`.

The contract tests then automatically verify it resolves and produces output.
```

