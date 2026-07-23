"""Contract tests between the seed data and the available generators.

These do NOT test the correctness of a third-party generator's math (that is
mathgenerator's responsibility). They assert only that every generator_name
the seed data relies on is a real generator that returns a (problem, solution)
pair — guarding against a library upgrade or a typo silently breaking a topic.
_make_problem resolves a name via LOCAL_GENERATORS then getattr(mathgenerator,
name); a name that no longer exists would otherwise surface as a 500 for a
student.

Local generators (ones we maintain) get a stronger determinism check in
LocalGeneratorTests, since their logic *is* our responsibility.
"""
import random
import re

import mathgenerator
from django.test import TestCase

from myapp.generators import LOCAL_GENERATORS
from myapp.management.commands.seed_topics import TOPICS
from myapp.models import Course, Topic
from myapp.views.problems import _make_problem_for_topic

# Third-party generators pick random inputs and can occasionally produce a
# falsy-but-valid answer (e.g. 0) or hit a random degenerate case. Call each a
# few times with a fixed seed so the contract check is deterministic across
# runs and a single unlucky draw can't flake CI.
_ATTEMPTS = 5


class SeedGeneratorContractTests(TestCase):
    def test_names_exist(self):
        # getGenList() yields [id, title, generator, name, category, params];
        # the snake_case name is what the seed data references.
        known = {
            name
            for _id, _title, _gen, name, _cat, _params in mathgenerator.getGenList()
        }
        known |= set(LOCAL_GENERATORS)
        seeded = {g for _topic, g in TOPICS if g is not None}
        missing = sorted(seeded - known)
        self.assertEqual(missing, [], f"Unknown generator names: {missing}")

    def test_names_produce_output(self):
        random.seed(0)
        broken = []
        for _topic_name, generator_name in TOPICS:
            if generator_name is None:
                continue
            generator = LOCAL_GENERATORS.get(generator_name) or getattr(
                mathgenerator, generator_name, None
            )
            if generator is None:
                broken.append(f"{generator_name!r}: not found")
                continue
            # Passes if any attempt yields well-formed output.
            ok, last_err = False, None
            for _ in range(_ATTEMPTS):
                try:
                    problem, solution = generator()
                    if problem and solution is not None:
                        ok = True
                        break
                    last_err = "empty output"
                except Exception as exc:  # noqa: BLE001 - report any failure mode
                    last_err = repr(exc)
            if not ok:
                broken.append(f"{generator_name!r}: {last_err}")
        self.assertEqual(broken, [], "Broken generators:\n" + "\n".join(broken))


class LocalGeneratorTests(TestCase):
    """Stronger checks for the generators we own."""

    def test_all_local_generators_return_well_formed_pairs(self):
        random.seed(0)
        for name, generator in LOCAL_GENERATORS.items():
            with self.subTest(generator=name):
                problem, solution = generator()
                self.assertIsInstance(problem, str)
                self.assertTrue(problem)
                self.assertIsInstance(solution, str)
                self.assertTrue(solution)

    def test_vertex_form_is_deterministic_under_seed(self):
        random.seed(42)
        problem1, solution1 = LOCAL_GENERATORS["vertex_form"]()
        random.seed(42)
        problem2, solution2 = LOCAL_GENERATORS["vertex_form"]()
        self.assertEqual((problem1, solution1), (problem2, solution2))


class ServedProblemQualityTests(TestCase):
    """Every seeded topic must serve typeable, well-formed problems.

    Runs each topic through the real serve path (`_make_problem_for_topic`, so
    the view's decimal-rounding pass applies) over many random samples and
    asserts the student never sees an answer they can't type or a malformed
    problem. This is the permanent guard behind the library-override sweep: it
    catches a regression (a new seed entry pointing at a broken library
    generator, or an override that stops rounding) the moment it ships.

    The checks encode the typeable-solution contract:
      - no LaTeX commands (a backslash followed by letters, e.g. \\frac, \\sqrt,
        \\times) in the solution — ASCII like ``csc(x)`` is fine, only escaped
        commands are banned;
      - no set/list bracket notation ({...} or [...]) in the solution;
      - no decimal carrying more than three fractional digits anywhere;
      - no float e-notation (``1e-11``) in the solution;
      - balanced ``$`` delimiters and no raw LaTeX leaking outside math mode in
        the problem text.
    """

    SAMPLES = 30
    LATEX_CMD = re.compile(r"\\[a-zA-Z]+")
    LONG_DECIMAL = re.compile(r"\d\.\d{4,}")
    E_NOTATION = re.compile(r"\d[eE][+-]?\d")

    @classmethod
    def setUpTestData(cls):
        # One Topic per seeded generator_name, attached to a throwaway course,
        # so `_make_problem_for_topic` can be exercised exactly as in production.
        course = Course.objects.create(course_name="Test", grade_level=0)
        cls.topics = [
            Topic.objects.create(
                topic_name=topic_name, course=course, generator_name=gen
            )
            for topic_name, gen in TOPICS
            if gen is not None
        ]

    def test_every_seeded_topic_serves_typeable_problems(self):
        random.seed(0)
        failures = []
        for topic in self.topics:
            for _ in range(self.SAMPLES):
                try:
                    result = _make_problem_for_topic(topic)
                except Exception as exc:  # noqa: BLE001 - a crash 500s the student
                    failures.append(f"{topic.generator_name}: raised {exc!r}")
                    break
                if result is None:
                    continue
                problem, solution = result["problem"], result["solution"]

                if self.LATEX_CMD.search(solution):
                    failures.append(f"{topic.generator_name}: LaTeX in solution {solution!r}")
                    break
                if any(c in solution for c in "{}[]"):
                    failures.append(f"{topic.generator_name}: bracket notation in solution {solution!r}")
                    break
                if self.E_NOTATION.search(solution):
                    failures.append(f"{topic.generator_name}: e-notation in solution {solution!r}")
                    break
                if self.LONG_DECIMAL.search(problem) or self.LONG_DECIMAL.search(solution):
                    failures.append(f"{topic.generator_name}: over-precise decimal in {problem!r} / {solution!r}")
                    break
                if problem.count("$") % 2 != 0:
                    failures.append(f"{topic.generator_name}: unbalanced $ in problem {problem!r}")
                    break
                # Text outside $...$ must not contain raw LaTeX commands.
                outside = "".join(problem.split("$")[::2])
                if self.LATEX_CMD.search(outside):
                    failures.append(f"{topic.generator_name}: raw LaTeX outside math mode {problem!r}")
                    break
        self.assertEqual(failures, [], "Non-typeable served problems:\n" + "\n".join(failures))
