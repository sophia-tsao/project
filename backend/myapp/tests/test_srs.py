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

    def test_interval_capped_at_max(self):
        # A success on an already-huge interval is clamped, not multiplied past
        # the cap, so a mastered topic still resurfaces.
        ease, interval, reps = srs.update(2.5, srs.MAX_INTERVAL, 10, 5)
        self.assertEqual(interval, srs.MAX_INTERVAL)

    def test_interval_just_below_cap_does_not_exceed_it(self):
        # round(interval * ease) would overshoot; the cap holds it at MAX_INTERVAL.
        big = srs.MAX_INTERVAL - 1
        ease, interval, reps = srs.update(2.5, big, 10, 5)
        self.assertLessEqual(interval, srs.MAX_INTERVAL)

    def test_inputs_not_mutated(self):
        # Pure function: returns new values, leaves the caller's state alone.
        args = (2.5, 6, 2)
        srs.update(*args, 5)
        self.assertEqual(args, (2.5, 6, 2))


class GradeThresholdTests(SimpleTestCase):
    """The pass/lapse boundary sits at PASSING_GRADE (q=3): q>=3 succeeds, q<3 lapses."""

    def test_lowest_passing_grade_advances(self):
        # q=3 is the lowest passing grade: a fresh item advances (reps 0 -> 1,
        # interval to 1 day) rather than lapsing.
        ease, interval, reps = srs.update(2.5, 0, 0, srs.PASSING_GRADE)
        self.assertEqual(interval, 1)
        self.assertEqual(reps, 1)

    def test_highest_failing_grade_lapses(self):
        # q=2 is just below the threshold: a mature item still collapses to a
        # relearn (reps -> 0, interval -> 1), confirming the boundary is q>=3.
        ease, interval, reps = srs.update(2.5, 30, 5, srs.PASSING_GRADE - 1)
        self.assertEqual(interval, 1)
        self.assertEqual(reps, 0)

    def test_passing_grade_advances_the_success_ladder(self):
        # A passing grade at repetitions==1 takes the second rung (6 days), not
        # the ease multiplier — the reps==1 branch is exercised on a pass.
        ease, interval, reps = srs.update(2.5, 1, 1, srs.PASSING_GRADE)
        self.assertEqual(interval, 6)
        self.assertEqual(reps, 2)

    def test_lapse_from_reps_one_resets_not_advances(self):
        # A lapse at the reps==1 boundary must reset (interval 1, reps 0), never
        # take the 6-day success rung — the pass/lapse branch wins over the
        # repetitions branch.
        ease, interval, reps = srs.update(2.5, 6, 1, srs.PASSING_GRADE - 1)
        self.assertEqual(interval, 1)
        self.assertEqual(reps, 0)
