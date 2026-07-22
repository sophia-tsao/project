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
│   └── myapp/        the single app (models, views, generators, tests, commands)
├── frontend/         React 19 SPA built with Vite (unit tests + Playwright e2e)
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
- **TopicReview** — per (user, topic) SM-2 scheduling state: `ease`, `interval`,
  `repetitions`, `due_date`. Solveki schedules *topics*, not individual problems
  (every problem is freshly generated), so the schedulable unit is the user's
  mastery of a topic. Kept separate from `UserTopicSelection` on purpose:
  deselecting a topic drops the selection row but preserves its review state for
  when it's selected again. A null `due_date` means "never practiced → due now".
- **DailyTopicGrade** — per (user, topic, date), supports the once-per-day
  grading rule (see below). Stores a snapshot of the topic's SM-2 state *before*
  the day's first grade plus the worst quality seen so far today, so repeated
  answers recompute from a fixed base instead of compounding.
- **Settings** — one-to-one per user; `language`, `questions_per_day`.
- **DailyDeck** — per user + date; `problems` (JSON list of `{problem, solution,
  topic_id}`) and `current_index`. `topic_id` attributes each stored problem
  back to its source topic so an answer can be graded against that topic.

### Endpoints (`backend/myapp/urls.py`)

| Method | Path | View |
| --- | --- | --- |
| GET | `auth/me/` | `me` |
| POST | `auth/google/` | `google_login` |
| POST | `auth/test-login/` | `test_login` (E2E only; 404 unless `ENABLE_TEST_LOGIN`) |
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

Deck logic (`_get_or_create_today_deck`, `_generate_problems`, `_deck_payload`)
builds a per-day deck of `questions_per_day` problems and discards stale
prior-day decks. Problems are chosen by spaced-repetition due order
(`_ordered_topics`): most-overdue topics first, never-practiced topics treated
as due today, not-yet-due topics only once the due ones run out (ties break by
topic id for a deterministic order). Distinct topics fill the deck first for
variety; when fewer topics are selected than `questions_per_day`, topics repeat
by cycling the same due order. `advance_deck` only ever steps an *existing* deck
forward — it never builds one. Otherwise a new day's deck (fresh at index 0)
could be advanced to index 1 without the student answering, stranding them on
"2 of N"; this bites because the correct-answer handler advances on a timer, so
finishing a problem just before midnight fires the advance after the day rolls
over.

When the student advances past a card, the client reports how it was answered
(`correct_first` / `correct_second` / `incorrect`) in the advance body; the
deck layer maps that outcome to an SM-2 quality grade and updates the card's
topic schedule (`_grade_topic`). The outcome is optional, so a stray advance
with no answer (the midnight-rollover case) simply doesn't grade.

"The day" is the *user's* local day, not the server's. The server clock is UTC
(`TIME_ZONE`), so every deck-touching request carries the client's local date
as `?today=YYYY-MM-DD` (`_client_today`); the deck then resets at the user's
midnight rather than UTC's. Requests without the param fall back to the server
date. The SPA also re-fetches the deck when the tab is refocused on a new local
day, so a page left open overnight rolls over instead of stranding the student
on yesterday's finished deck.

## Spaced repetition (SM-2)

Solveki schedules practice with SuperMemo-2. The design splits cleanly into
*pure scheduling math* and *stateful application*:

- **`backend/myapp/srs.py`** is the whole SM-2 algorithm and nothing else: pure
  functions with no database, request, or clock access. It maps
  `(ease, interval, repetitions, quality) -> (ease, interval, repetitions)` and
  can be reasoned about and unit-tested in isolation. State is the SM-2 triple:
  `ease` (interval multiplier, starts 2.5, floored at 1.3), `interval` (days to
  the next review), and `repetitions` (consecutive successful recalls, reset on
  a lapse). A successful recall (`quality >= 3`) grows the interval — 1 day, then
  6, then `interval * ease` — capped at `MAX_INTERVAL` (365 days, borrowed from
  Anki's notion of a max interval but tuned so a mastered topic still resurfaces
  at least yearly). A lapse resets `repetitions` to 0 and `interval` to 1 day.
- **The deck layer owns persistence, dates, and grade derivation.**
  `_grade_topic` (in `views/deck.py`) turns an answer outcome into a quality
  grade (`correct_first` → 5, `correct_second` → 3, `incorrect` → 1), calls
  `srs.update`, and writes the topic's `TopicReview` (including its new
  `due_date = today + interval`). `_ordered_topics` reads those `due_date`s to
  order the deck but never computes them.

### Filling the deck: due-weighted dose

SM-2 schedules one review per item on its due date, but Solveki always fills the
day to `questions_per_day` so a student with few selected topics still gets a
full practice session. Rather than repeat topics evenly, `_generate_problems`
weights how much of the deck each topic gets by *how overdue* it is
(`_due_weight`): a topic due today or overdue takes a larger share than one whose
next review is days out. Every selected topic keeps at least one slot (a variety
floor), and the remaining slots are split by weight using the largest-remainder
method so the counts stay deterministic and sum to exactly `questions_per_day`.
This carries SM-2's core signal — practice the due thing more — into the *within-
day dose*, not just the ordering: after a lapse, that topic both leads the deck
and occupies more of it the next day, while a mastered topic recedes to its floor
slot. Equal-priority topics reduce to an even split.

### The once-per-day grading rule

A topic can appear more than once in a day's deck (the deck repeats topics when
few are selected). The rule: **the first answer for a topic each day sets its
schedule; later repeats may only pull it down** — a second miss re-grades as a
lapse, but a later success can't raise a schedule the student already got wrong.

To apply that without compounding (repeated misses must not drop ease over and
over), `DailyTopicGrade` snapshots the topic's SM-2 state *before* the day's
first grade and records the worst quality applied so far today. Each occurrence
recomputes the `TopicReview` from that fixed snapshot using
`min(applied_quality, this_quality)`, so the day's net effect is always "one
SM-2 update from a single base", never a chain of them.

### Tests

`tests/test_srs.py` unit-tests the pure algorithm (including grade boundaries);
`tests/test_srs_integration.py` covers the deck-layer wiring (due ordering,
grading, the once-per-day rule) end to end.

## Frontend (React 19 + Vite 8)

Located at `frontend/` (top-level, a sibling of `backend/`). Uses KaTeX for
math rendering and oxlint for
linting. `App.jsx` is a top-level router-by-state (`math`, `courses`,
`settings` pages; `LoginPage` when unauthenticated). Practice UI lives in
`MathProblem.jsx` / `MathProblemDisplay.jsx` / `MathProblemResponse.jsx`
(problem rendering, answer box, two-attempt flow); course selection in
`CourseList.jsx` / `CourseBar.jsx`; auth helpers in `auth.js`.

## Testing

Three layers. Backend unit tests (`backend/myapp/tests/`) and frontend unit
tests (Vitest, colocated `*.test.jsx`) cover units in isolation. A Playwright
end-to-end suite (`frontend/e2e/`) drives a real browser through the built SPA
against a live Django API, covering the login gate, topic selection, the daily
deck flow, and settings. Since Google OAuth can't run headless, E2E auth goes
through `POST /auth/test-login/`, gated behind `ENABLE_TEST_LOGIN` (404 when
off) and resetting the shared test user's state on each call. The suite runs
serially (one shared backend user → no DB isolation between tests) and has its
own CI workflow (`.github/workflows/e2e-tests.yml`). See the README for how to
run it.

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

### Resolving a name to a generator (`views/problems.py`, `_make_problem`)

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

