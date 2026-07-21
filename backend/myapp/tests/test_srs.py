"""Tests for the SM-2 scheduling math in `myapp.srs`.

The functions under test are pure (no DB, no clock), so these use SimpleTestCase.
"""
from django.test import SimpleTestCase

from myapp import srs


class UpdateEaseTests(SimpleTestCase):
    def test_perfect_recall_raises_ease(self):
        # q=5 applies the full +0.1 bonus.
        self.assertAlmostEqual(srs.update_ease(2.5, 5), 2.6)

    def test_passing_but_hard_lowers_ease(self):
        # q=3 (correct but hard) pulls ease down.
        self.assertAlmostEqual(srs.update_ease(2.5, 3), 2.36)

    def test_ease_never_drops_below_floor(self):
        # Repeated failures from a low starting ease clamp at 1.3, not below.
        self.assertEqual(srs.update_ease(1.3, 0), srs.MIN_EASE)
        self.assertEqual(srs.update_ease(1.4, 0), srs.MIN_EASE)


class UpdateTests(SimpleTestCase):
    def test_first_success_schedules_one_day(self):
        ease, interval, reps = srs.update(2.5, 0, 0, 5)
        self.assertEqual(interval, 1)
        self.assertEqual(reps, 1)

    def test_second_success_schedules_six_days(self):
        ease, interval, reps = srs.update(2.5, 1, 1, 5)
        self.assertEqual(interval, 6)
        self.assertEqual(reps, 2)

    def test_third_success_multiplies_by_ease(self):
        # After two reviews: interval 6, reps 2. Third success -> round(6 * ease).
        ease, interval, reps = srs.update(2.5, 6, 2, 5)
        self.assertEqual(interval, round(6 * ease))
        self.assertEqual(reps, 3)

    def test_lapse_resets_repetitions_and_interval(self):
        # A wrong answer on a mature item collapses it back to a 1-day interval.
        ease, interval, reps = srs.update(2.5, 30, 5, 1)
        self.assertEqual(interval, 1)
        self.assertEqual(reps, 0)

    def test_lapse_still_lowers_ease(self):
        # The ease update applies on a lapse too, so a missed item grows slower later.
        ease, interval, reps = srs.update(2.5, 30, 5, 1)
        self.assertLess(ease, 2.5)

    def test_lapse_respects_ease_floor(self):
        ease, interval, reps = srs.update(1.3, 30, 5, 0)
        self.assertEqual(ease, srs.MIN_EASE)

    def test_inputs_not_mutated(self):
        # Pure function: returns new values, leaves the caller's state alone.
        args = (2.5, 6, 2)
        srs.update(*args, 5)
        self.assertEqual(args, (2.5, 6, 2))
