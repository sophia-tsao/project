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

import mathgenerator
from django.test import TestCase

from myapp.generators import LOCAL_GENERATORS
from myapp.management.commands.seed_topics import TOPICS

# Third-party generators pick random inputs and can occasionally produce a
# falsy-but-valid answer (e.g. 0) or hit a random degenerate case. Call each a
# few times with a fixed seed so the contract check is deterministic across
# runs and a single unlucky draw can't flake CI.
_ATTEMPTS = 5


class SeedGeneratorContractTests(TestCase):
    def test_names_exist(self):
        known = {name for name, _category in mathgenerator.get_gen_list()}
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
