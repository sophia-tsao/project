"""End-to-end integration tests for SM-2 spaced repetition.

Where `test_srs.py` unit-tests the pure scheduling math and `test_deck.py`
unit-tests each deck helper in isolation, this exercises the *whole* SM-2 loop
through the real HTTP API — URL routing, the deck views, grading, `myapp.srs`,
and the database — across multiple simulated days.

"Days" are simulated with the `?today=YYYY-MM-DD` query param the client sends
(see `_client_today` in views/deck.py), so a test can walk a user through a week
of practice without touching the clock. Each day the flow is: GET /deck/ to build
or load the day's deck, then POST /deck/advance/ with an `outcome` to answer and
grade the current card.

The `addition` generator is mocked so problem text is deterministic; scheduling,
not problem content, is what's under test.
"""
import datetime
import json
from unittest import mock

from django.test import TestCase, Client

from myapp.models import DailyDeck, Settings, TopicReview
from .factories import make_user, make_course, make_topic, select


@mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
class SM2LifecycleTests(TestCase):
    """Drive the full spaced-repetition loop through the HTTP endpoints."""

    START = datetime.date(2026, 7, 22)

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)
        self.course = make_course()

    # --- helpers -----------------------------------------------------------

    def _day(self, date):
        return date.isoformat()

    def _load_deck(self, date):
        """GET today's deck for `date`, returning the parsed payload."""
        return self.client.get(f"/deck/?today={self._day(date)}").json()

    def _answer_current(self, date, outcome):
        """POST an advance for `date`, grading the current card with `outcome`."""
        return self.client.post(
            f"/deck/advance/?today={self._day(date)}",
            data=json.dumps({"outcome": outcome}),
            content_type="application/json",
        ).json()

    def _review(self, topic):
        return TopicReview.objects.get(user=self.user, topic=topic)

    def _set_questions_per_day(self, n):
        Settings.objects.update_or_create(
            user=self.user, defaults={"questions_per_day": n}
        )

    # --- tests -------------------------------------------------------------

    def test_correct_answers_grow_the_interval_across_days(self, _gen):
        # A single topic answered correctly each day should walk the SM-2
        # success ladder: due tomorrow (interval 1), then +6 days, then the
        # ease-multiplied step — all driven purely through the HTTP loop.
        topic = make_topic(self.course, generator_name="addition")
        select(self.user, topic)
        self._set_questions_per_day(1)

        day1 = self.START
        self._load_deck(day1)
        self._answer_current(day1, "correct_first")
        review = self._review(topic)
        self.assertEqual(review.interval, 1)
        self.assertEqual(review.repetitions, 1)
        self.assertEqual(review.due_date, day1 + datetime.timedelta(days=1))

        # Second successful review, on the day it comes due.
        day2 = review.due_date
        self._load_deck(day2)
        self._answer_current(day2, "correct_first")
        review = self._review(topic)
        self.assertEqual(review.interval, 6)
        self.assertEqual(review.repetitions, 2)
        self.assertEqual(review.due_date, day2 + datetime.timedelta(days=6))

        # Third success multiplies the interval by the ease factor (> 6 days).
        day3 = review.due_date
        self._load_deck(day3)
        self._answer_current(day3, "correct_first")
        review = self._review(topic)
        self.assertEqual(review.repetitions, 3)
        self.assertGreater(review.interval, 6)
        self.assertEqual(review.due_date, day3 + datetime.timedelta(days=review.interval))

    def test_wrong_answer_reschedules_topic_for_the_next_day(self, _gen):
        # A lapse must bring the topic back tomorrow: interval 1, reps reset.
        topic = make_topic(self.course, generator_name="addition")
        select(self.user, topic)
        self._set_questions_per_day(1)

        day1 = self.START
        self._load_deck(day1)
        self._answer_current(day1, "incorrect")
        review = self._review(topic)
        self.assertEqual(review.interval, 1)
        self.assertEqual(review.repetitions, 0)
        self.assertEqual(review.due_date, day1 + datetime.timedelta(days=1))

    def test_due_topic_sorts_ahead_of_scheduled_topic_next_day(self, _gen):
        # The payoff of scheduling: after one day, a topic answered correctly
        # (now due in 6+ days) must fall behind a topic that lapsed (due
        # tomorrow). The next day's deck should lead with the lapsed topic.
        mastered = make_topic(self.course, topic_name="Mastered", generator_name="addition")
        lapsed = make_topic(self.course, topic_name="Lapsed", generator_name="addition")
        select(self.user, mastered)
        select(self.user, lapsed)
        # Give both a couple of prior successes so "mastered" earns a long
        # interval and the ordering difference is unambiguous.
        for t in (mastered, lapsed):
            TopicReview.objects.update_or_create(
                user=self.user, topic=t,
                defaults={"ease": 2.5, "interval": 6, "repetitions": 2,
                          "due_date": self.START},
            )
        self._set_questions_per_day(2)

        day1 = self.START
        self._load_deck(day1)
        # Deck holds one card per topic in due order. Answer both: the first
        # card's topic correctly, the second's incorrectly. We don't rely on
        # which topic is which card — we grade by reading the stored deck.
        deck = DailyDeck.objects.get(user=self.user, date=day1)
        # Reorder our answers so "mastered" is graded correct and "lapsed" wrong
        # regardless of deck order, by advancing twice with per-card outcomes.
        outcomes = {mastered.id: "correct_first", lapsed.id: "incorrect"}
        for card in deck.problems[:2]:
            self._answer_current(day1, outcomes[card["topic_id"]])

        mastered_due = self._review(mastered).due_date
        lapsed_due = self._review(lapsed).due_date
        self.assertGreater(mastered_due, lapsed_due)  # mastered pushed out further
        self.assertEqual(lapsed_due, day1 + datetime.timedelta(days=1))

        # Next day: the lapsed topic is due, the mastered one is not. The deck
        # must lead with the lapsed topic (most-due-first ordering).
        day2 = day1 + datetime.timedelta(days=1)
        self._load_deck(day2)
        deck2 = DailyDeck.objects.get(user=self.user, date=day2)
        self.assertEqual(deck2.problems[0]["topic_id"], lapsed.id)

    def test_lapsed_topic_gets_more_of_the_deck_next_day(self, _gen):
        # The SM-2 dose signal end to end: with two topics and a 10-card day,
        # answering topic 1 correctly (pushed 6+ days out) and topic 2 wrong
        # (due tomorrow) must make topic 2 occupy MORE of the next day's deck —
        # not the flat 5/5 split. Both still appear (variety floor).
        from collections import Counter

        mastered = make_topic(self.course, topic_name="Mastered", generator_name="addition")
        lapsed = make_topic(self.course, topic_name="Lapsed", generator_name="addition")
        select(self.user, mastered)
        select(self.user, lapsed)
        for t in (mastered, lapsed):
            TopicReview.objects.update_or_create(
                user=self.user, topic=t,
                defaults={"ease": 2.5, "interval": 6, "repetitions": 2,
                          "due_date": self.START},
            )
        self._set_questions_per_day(10)

        day1 = self.START
        self._load_deck(day1)
        deck = DailyDeck.objects.get(user=self.user, date=day1)
        outcomes = {mastered.id: "correct_first", lapsed.id: "incorrect"}
        # Grade every card in day 1's deck so both topics get their day's grade.
        for card in deck.problems:
            self._answer_current(day1, outcomes[card["topic_id"]])

        # Next day: lapsed is due, mastered is scheduled out. Lapsed should take
        # the larger share of the deck, and both should still be present.
        day2 = day1 + datetime.timedelta(days=1)
        self._load_deck(day2)
        deck2 = DailyDeck.objects.get(user=self.user, date=day2)
        counts = Counter(c["topic_id"] for c in deck2.problems)
        self.assertEqual(sum(counts.values()), 10)
        self.assertGreater(counts[lapsed.id], counts[mastered.id])
        self.assertGreaterEqual(counts[mastered.id], 1)

    def test_new_topic_enters_rotation_and_is_scheduled_after_first_review(self, _gen):
        # A never-practiced topic has no TopicReview row (treated as due now),
        # so it appears immediately; answering it creates its schedule.
        topic = make_topic(self.course, generator_name="addition")
        select(self.user, topic)
        self._set_questions_per_day(1)

        day1 = self.START
        payload = self._load_deck(day1)
        self.assertEqual(payload["current_number"], 1)
        self.assertFalse(
            TopicReview.objects.filter(user=self.user, topic=topic).exists()
        )

        self._answer_current(day1, "correct_first")
        self.assertTrue(
            TopicReview.objects.filter(user=self.user, topic=topic).exists()
        )

    def test_repeated_topic_in_one_day_only_grades_down(self, _gen):
        # With one topic and a multi-card day, the topic repeats within the deck.
        # The once-per-day rule: the first answer sets the schedule; a later
        # passing repeat can't raise it, but a later miss pulls it down.
        topic = make_topic(self.course, generator_name="addition")
        select(self.user, topic)
        self._set_questions_per_day(3)

        day1 = self.START
        self._load_deck(day1)

        # First card correct: schedules the topic out one day.
        self._answer_current(day1, "correct_first")
        after_first = self._review(topic)
        self.assertEqual(after_first.interval, 1)
        self.assertEqual(after_first.repetitions, 1)

        # Second card (same topic) correct again: must NOT advance the schedule.
        self._answer_current(day1, "correct_first")
        after_second = self._review(topic)
        self.assertEqual(after_second.interval, after_first.interval)
        self.assertEqual(after_second.repetitions, after_first.repetitions)

        # Third card (same topic) wrong: pulls the schedule down to a lapse.
        self._answer_current(day1, "incorrect")
        after_third = self._review(topic)
        self.assertEqual(after_third.repetitions, 0)
        self.assertEqual(after_third.due_date, day1 + datetime.timedelta(days=1))

    def test_full_week_of_practice_keeps_a_consistent_schedule(self, _gen):
        # A longer walk: practice one topic correctly whenever it comes due over
        # a simulated stretch, and assert the schedule stays monotonic and the
        # due_date always equals today + interval (the invariant the deck relies
        # on for ordering). Guards against drift between reps/interval/due_date.
        topic = make_topic(self.course, generator_name="addition")
        select(self.user, topic)
        self._set_questions_per_day(1)

        day = self.START
        last_interval = 0
        for _ in range(5):
            self._load_deck(day)
            self._answer_current(day, "correct_first")
            review = self._review(topic)
            # Each successful review is due exactly `interval` days out...
            self.assertEqual(review.due_date, day + datetime.timedelta(days=review.interval))
            # ...and the interval never shrinks on an unbroken success streak.
            self.assertGreaterEqual(review.interval, last_interval)
            last_interval = review.interval
            day = review.due_date
