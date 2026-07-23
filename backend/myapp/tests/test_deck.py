"""Tests for problem generation and the daily deck lifecycle.

The `addition` generator (which the test topics use) is mocked so problem
text/solutions are deterministic and the rounding logic can be asserted
precisely.
"""
import datetime
import json
from collections import Counter
from unittest import mock

from django.test import TestCase, Client

from myapp.models import (
    DailyDeck, Settings, Topic, TopicReview, DailyTopicGrade, UserTopicSelection,
)
from myapp import views
from myapp.views.deck import _select_deck_topics, _generate_problems, _grade_topic
from .factories import make_user, make_course, make_topic, select


class MakeProblemTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.course = make_course()
        self.topic = make_topic(self.course, generator_name="addition")

    def test_no_topics_returns_none(self):
        self.assertIsNone(views._make_problem(self.user))

    @mock.patch("myapp.views.mathgenerator.addition")
    def test_integer_solution_not_rounded(self, mock_gen):
        select(self.user, self.topic)
        # An integer solution is stripped of its '$' delimiters but not rounded.
        mock_gen.return_value = ("$2+2=$", "$4$")
        result = views._make_problem(self.user)
        self.assertEqual(result["solution"], "4")
        self.assertNotIn("Round", result["problem"])

    @mock.patch("myapp.views.mathgenerator.addition")
    def test_long_decimal_is_rounded_and_annotated(self, mock_gen):
        select(self.user, self.topic)
        mock_gen.return_value = ("What is 1/3?", "0.3333333")
        result = views._make_problem(self.user)
        self.assertEqual(result["solution"], "0.333")
        self.assertIn("Round to the nearest thousandth", result["problem"])

    @mock.patch("myapp.views.mathgenerator.addition")
    def test_short_decimal_not_annotated(self, mock_gen):
        select(self.user, self.topic)
        mock_gen.return_value = ("Q", "0.5")
        result = views._make_problem(self.user)
        self.assertEqual(result["solution"], "0.5")
        self.assertNotIn("Round", result["problem"])

    @mock.patch("myapp.views.mathgenerator.addition")
    def test_nonnumeric_solution_passes_through(self, mock_gen):
        select(self.user, self.topic)
        mock_gen.return_value = ("Simplify", "$x + 1$")
        result = views._make_problem(self.user)
        self.assertEqual(result["solution"], "x + 1")

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("Q", "1"))
    def test_problem_carries_source_topic_id(self, mock_gen):
        # Each generated problem records which topic it came from, so an answer
        # can later be attributed to that topic for spaced-repetition scheduling.
        select(self.user, self.topic)
        result = views._make_problem(self.user)
        self.assertEqual(result["topic_id"], self.topic.id)


class GenerateProblemTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)
        self.course = make_course()
        self.topic = make_topic(self.course, generator_name="addition")

    def test_no_topics_selected(self):
        response = self.client.get("/problem/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["no_topics"])

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_returns_problem(self, mock_gen):
        select(self.user, self.topic)
        response = self.client.get("/problem/")
        data = response.json()
        self.assertIn("problem", data)
        self.assertEqual(data["solution"], "2")


class DeckTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)
        self.course = make_course()
        self.topic = make_topic(self.course, generator_name="addition")

    def test_deck_empty_when_no_topics(self):
        response = self.client.get("/deck/")
        self.assertTrue(response.json()["no_topics"])

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_deck_built_and_paged(self, mock_gen):
        select(self.user, self.topic)
        Settings.load(self.user)  # default questions_per_day = 10
        Settings.objects.filter(user=self.user).update(questions_per_day=3)

        data = self.client.get("/deck/").json()
        self.assertEqual(data["total"], 3)
        self.assertEqual(data["current_number"], 1)

        # Advance through the deck.
        data = self.client.post("/deck/advance/").json()
        self.assertEqual(data["current_number"], 2)
        self.client.post("/deck/advance/")
        data = self.client.post("/deck/advance/").json()
        self.assertTrue(data.get("completed"))
        self.assertEqual(data["total"], 3)

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_stored_deck_entries_carry_topic_id(self, mock_gen):
        # Stored problems remember their source topic so answers can be graded
        # against it; the client-facing payload still omits it (see _deck_payload).
        select(self.user, self.topic)
        Settings.objects.update_or_create(
            user=self.user, defaults={"questions_per_day": 2}
        )
        self.client.get("/deck/")
        deck = DailyDeck.objects.get(user=self.user)
        self.assertTrue(all(p["topic_id"] == self.topic.id for p in deck.problems))

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_legacy_deck_without_topic_id_tops_up_without_error(self, mock_gen):
        # A deck persisted before topic attribution existed has entries with no
        # topic_id. Topping it up must not crash reading the in-deck topic ids.
        select(self.user, self.topic)
        Settings.objects.update_or_create(
            user=self.user, defaults={"questions_per_day": 3}
        )
        DailyDeck.objects.create(
            user=self.user,
            date=datetime.date(2026, 7, 21),
            problems=[{"problem": "old", "solution": "1"}],  # no topic_id
            current_index=0,
        )
        data = self.client.get("/deck/?today=2026-07-21").json()
        self.assertEqual(data["total"], 3)

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_new_day_rebuilds_deck(self, mock_gen):
        select(self.user, self.topic)
        Settings.objects.update_or_create(
            user=self.user, defaults={"questions_per_day": 2}
        )
        # Simulate a stale deck from yesterday.
        yesterday = datetime.date(2020, 1, 1)
        DailyDeck.objects.create(
            user=self.user, date=yesterday, problems=[{"problem": "old", "solution": "1"}]
        )
        self.client.get("/deck/")
        self.assertFalse(DailyDeck.objects.filter(user=self.user, date=yesterday).exists())
        deck = DailyDeck.objects.get(user=self.user)
        self.assertEqual(len(deck.problems), 2)

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_advance_on_new_day_does_not_skip_past_card_one(self, mock_gen):
        # Regression: advancing must never *build* a deck. The "correct answer"
        # handler advances on a timer, so finishing a problem just before
        # midnight can make the day's first backend call an advance. If advance
        # created-then-stepped the new day's deck, the student would land on
        # "2 of N" having answered nothing today. It must leave them on card 1.
        select(self.user, self.topic)
        Settings.objects.update_or_create(
            user=self.user, defaults={"questions_per_day": 3}
        )
        # Finish yesterday's deck.
        self.client.get("/deck/?today=2026-07-19")
        for _ in range(3):
            self.client.post("/deck/advance/?today=2026-07-19")
        # New day, first call is an advance (no deck exists yet for today).
        data = self.client.post("/deck/advance/?today=2026-07-20").json()
        self.assertFalse(data.get("completed"))
        self.assertEqual(data["current_number"], 1)
        self.assertEqual(data["total"], 3)
        deck = DailyDeck.objects.get(user=self.user, date=datetime.date(2026, 7, 20))
        self.assertEqual(deck.current_index, 0)

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_new_day_get_then_stray_advance_stays_on_card_one(self, mock_gen):
        # The real new-day sequence: the SPA mounts and GETs the deck (building
        # a fresh one at index 0), and *then* a leftover advance timer from
        # finishing yesterday's last card fires. That stray advance must not
        # step the fresh deck to card 2 — the student answered nothing today.
        select(self.user, self.topic)
        Settings.objects.update_or_create(
            user=self.user, defaults={"questions_per_day": 3}
        )
        # Finish yesterday's deck.
        self.client.get("/deck/?today=2026-07-19")
        for _ in range(3):
            self.client.post("/deck/advance/?today=2026-07-19")

        # New day: GET builds the fresh deck at card 1...
        got = self.client.get("/deck/?today=2026-07-20").json()
        self.assertEqual(got["current_number"], 1)
        # ...then the stray advance timer fires. It was scheduled while the
        # student was finishing yesterday's last card (card 3), so it carries
        # from_number=3, which no longer matches the fresh deck on card 1. The
        # backend must ignore it and leave the student on card 1.
        advanced = self.client.post(
            "/deck/advance/?today=2026-07-20",
            data=json.dumps({"outcome": "correct_first", "from_number": 3}),
            content_type="application/json",
        ).json()
        self.assertEqual(advanced["current_number"], 1)
        deck = DailyDeck.objects.get(user=self.user, date=datetime.date(2026, 7, 20))
        self.assertEqual(deck.current_index, 0)

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_deck_resets_on_client_local_day_not_server_utc_day(self, mock_gen):
        # The server clock is UTC, but the deck must reset at the *user's* local
        # midnight. A user ahead of UTC can be a calendar day ahead of the
        # server; the client sends that day as ?today=. Yesterday's finished
        # deck must not be what they see on their new morning.
        select(self.user, self.topic)
        Settings.objects.update_or_create(
            user=self.user, defaults={"questions_per_day": 2}
        )
        # A completed deck dated to the server's current day.
        from django.utils import timezone
        server_today = timezone.localdate()
        DailyDeck.objects.create(
            user=self.user,
            date=server_today,
            problems=[{"problem": "old", "solution": "1"}],
            current_index=1,  # finished
        )
        # The client is already on the next calendar day.
        client_tomorrow = server_today + datetime.timedelta(days=1)
        data = self.client.get(f"/deck/?today={client_tomorrow.isoformat()}").json()

        # A fresh deck for the client's day — on card 1, not the finished deck.
        self.assertFalse(data.get("completed"))
        self.assertEqual(data["current_number"], 1)
        self.assertEqual(data["total"], 2)
        # The stale server-day deck is discarded.
        self.assertFalse(
            DailyDeck.objects.filter(user=self.user, date=server_today).exists()
        )

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_malformed_today_param_falls_back_to_server_date(self, mock_gen):
        select(self.user, self.topic)
        Settings.objects.update_or_create(
            user=self.user, defaults={"questions_per_day": 2}
        )
        # A garbage ?today= must not 500; it falls back to the server date.
        data = self.client.get("/deck/?today=not-a-date").json()
        self.assertEqual(data["current_number"], 1)
        self.assertEqual(data["total"], 2)

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_empty_deck_rebuilt_once_topics_selected(self, mock_gen):
        # First visit with no topics yields an empty deck for today.
        self.client.get("/deck/")
        deck = DailyDeck.objects.get(user=self.user)
        self.assertEqual(deck.problems, [])

        # After selecting a topic, revisiting fills today's existing deck.
        select(self.user, self.topic)
        Settings.objects.update_or_create(
            user=self.user, defaults={"questions_per_day": 2}
        )
        data = self.client.get("/deck/").json()
        self.assertEqual(data["total"], 2)


class SelectDeckTopicsTests(TestCase):
    """The spaced-repetition topic selector (Option A due order + Option 2 fill)."""

    def setUp(self):
        self.user = make_user()
        self.course = make_course()
        self.today = datetime.date(2026, 7, 21)

    def _topic(self, name, generator_name="addition", selected=True):
        topic = make_topic(self.course, topic_name=name, generator_name=generator_name)
        if selected:
            select(self.user, topic)
        return topic

    def _review(self, topic, due_date, **kwargs):
        return TopicReview.objects.create(
            user=self.user, topic=topic, due_date=due_date, **kwargs
        )

    def test_empty_when_no_topics_selected(self):
        # A topic exists but isn't selected -> nothing to review.
        self._topic("Unselected", selected=False)
        self.assertEqual(_select_deck_topics(self.user, self.today, 5), [])

    def test_ignores_topics_without_a_generator(self):
        self._topic("No generator", generator_name=None)
        self.assertEqual(_select_deck_topics(self.user, self.today, 5), [])

    def test_never_reviewed_topic_is_due_now(self):
        # No TopicReview row => treated as due today, so it's selected.
        t = self._topic("Fresh")
        self.assertEqual(_select_deck_topics(self.user, self.today, 5), [t])

    def test_orders_most_overdue_first(self):
        recent = self._topic("Recent")
        old = self._topic("Old")
        middle = self._topic("Middle")
        self._review(recent, self.today - datetime.timedelta(days=1))
        self._review(old, self.today - datetime.timedelta(days=10))
        self._review(middle, self.today - datetime.timedelta(days=5))
        result = _select_deck_topics(self.user, self.today, 5)
        self.assertEqual(result, [old, middle, recent])

    def test_tops_up_with_next_soonest_when_few_are_due(self):
        # One overdue, two not-yet-due. count=3 pulls the due one first, then
        # the soonest future topic, then the later one.
        due = self._topic("Due")
        soon = self._topic("Soon")
        later = self._topic("Later")
        self._review(due, self.today - datetime.timedelta(days=2))
        self._review(soon, self.today + datetime.timedelta(days=3))
        self._review(later, self.today + datetime.timedelta(days=30))
        result = _select_deck_topics(self.user, self.today, 3)
        self.assertEqual(result, [due, soon, later])

    def test_full_deck_even_when_nothing_is_due(self):
        # Key invariant: "nothing due" still yields a full deck via top-up, so
        # an empty result means "no topics", never "nothing to review today".
        a = self._topic("A")
        b = self._topic("B")
        self._review(a, self.today + datetime.timedelta(days=5))
        self._review(b, self.today + datetime.timedelta(days=10))
        result = _select_deck_topics(self.user, self.today, 5)
        self.assertEqual(result, [a, b])

    def test_caps_at_count(self):
        for i in range(5):
            self._topic(f"T{i}")
        result = _select_deck_topics(self.user, self.today, 3)
        self.assertEqual(len(result), 3)

    def test_excludes_given_topic_ids(self):
        a = self._topic("A")
        b = self._topic("B")
        result = _select_deck_topics(self.user, self.today, 5, exclude={a.id})
        self.assertEqual(result, [b])

    def test_excluding_all_yields_empty(self):
        a = self._topic("A")
        result = _select_deck_topics(self.user, self.today, 5, exclude={a.id})
        self.assertEqual(result, [])

    def test_zero_count_yields_empty(self):
        self._topic("A")
        self.assertEqual(_select_deck_topics(self.user, self.today, 0), [])

    def test_only_selecting_users_topics(self):
        # Another user's selection must not leak into this user's deck.
        other = make_user()
        mine = self._topic("Mine")
        theirs = make_topic(self.course, topic_name="Theirs", generator_name="addition")
        select(other, theirs)
        result = _select_deck_topics(self.user, self.today, 5)
        self.assertEqual(result, [mine])


class GenerateProblemsTests(TestCase):
    """Filling a deck to exactly `count`: distinct topics first, then repeats.

    The `addition` generator echoes its topic id back as the problem text so a
    generated problem can be traced to its source topic without a real generator.
    """

    def setUp(self):
        self.user = make_user()
        self.course = make_course()
        self.today = datetime.date(2026, 7, 21)

    def _topic(self, name, generator_name="addition"):
        topic = make_topic(self.course, topic_name=name, generator_name=generator_name)
        select(self.user, topic)
        return topic

    def _review(self, topic, due_date):
        return TopicReview.objects.create(user=self.user, topic=topic, due_date=due_date)

    def test_empty_when_no_topics(self):
        self.assertEqual(_generate_problems(self.user, 5, self.today), [])

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("Q", "1"))
    def test_distinct_topics_used_before_repeating(self, mock_gen):
        # Three topics, count 3 -> each appears exactly once.
        topics = [self._topic(f"T{i}") for i in range(3)]
        problems = _generate_problems(self.user, 3, self.today)
        self.assertEqual(len(problems), 3)
        self.assertEqual(
            sorted(p["topic_id"] for p in problems),
            sorted(t.id for t in topics),
        )

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("Q", "1"))
    def test_repeats_to_fill_when_fewer_topics_than_count(self, mock_gen):
        # One topic, count 3 -> the deck still reaches 3, repeating that topic.
        topic = self._topic("Only")
        problems = _generate_problems(self.user, 3, self.today)
        self.assertEqual(len(problems), 3)
        self.assertTrue(all(p["topic_id"] == topic.id for p in problems))

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("Q", "1"))
    def test_fills_in_due_order_most_overdue_first(self, mock_gen):
        old = self._topic("Old")
        recent = self._topic("Recent")
        self._review(old, self.today - datetime.timedelta(days=10))
        self._review(recent, self.today - datetime.timedelta(days=1))
        problems = _generate_problems(self.user, 2, self.today)
        self.assertEqual([p["topic_id"] for p in problems], [old.id, recent.id])

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("Q", "1"))
    def test_topup_adds_fresh_topic_before_repeating(self, mock_gen):
        # A deck already holding topic A, topped up by 2, with topics A and B
        # selected: B (fresh) comes before A repeats.
        a = self._topic("A")
        b = self._topic("B")
        extra = _generate_problems(self.user, 2, self.today, existing=[a.id])
        self.assertEqual([p["topic_id"] for p in extra], [b.id, a.id])

    def test_broken_generator_does_not_loop_forever(self):
        # An unresolvable generator name yields no problems rather than hanging.
        self._topic("Broken", generator_name="not_a_real_generator")
        self.assertEqual(_generate_problems(self.user, 3, self.today), [])

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("Q", "1"))
    def test_overdue_topic_gets_more_slots_than_not_due_one(self, mock_gen):
        # The SM-2 dose signal: with two topics filling a 10-card deck, the
        # topic that's due today should occupy far more of the deck than one
        # whose next review is a week out — not an even 5/5 split.
        due = self._topic("Due")
        scheduled = self._topic("Scheduled")
        self._review(due, self.today)  # due today
        self._review(scheduled, self.today + datetime.timedelta(days=6))
        problems = _generate_problems(self.user, 10, self.today)
        self.assertEqual(len(problems), 10)
        counts = Counter(p["topic_id"] for p in problems)
        # Both still appear (variety floor), but the due topic dominates.
        self.assertGreater(counts[due.id], counts[scheduled.id])
        self.assertGreaterEqual(counts[scheduled.id], 1)
        self.assertEqual(counts[due.id] + counts[scheduled.id], 10)

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("Q", "1"))
    def test_more_overdue_topic_outweighs_less_overdue_one(self, mock_gen):
        # Among two overdue topics, the more overdue gets the larger share.
        very = self._topic("VeryOverdue")
        slightly = self._topic("SlightlyOverdue")
        self._review(very, self.today - datetime.timedelta(days=9))
        self._review(slightly, self.today - datetime.timedelta(days=1))
        problems = _generate_problems(self.user, 10, self.today)
        counts = Counter(p["topic_id"] for p in problems)
        self.assertGreater(counts[very.id], counts[slightly.id])

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("Q", "1"))
    def test_equally_due_topics_split_evenly(self, mock_gen):
        # Equal priority => equal dose: two topics both due today split a
        # 10-card deck 5/5 (the weighting reduces to the old round-robin).
        a = self._topic("A")
        b = self._topic("B")
        self._review(a, self.today)
        self._review(b, self.today)
        problems = _generate_problems(self.user, 10, self.today)
        counts = Counter(p["topic_id"] for p in problems)
        self.assertEqual(counts[a.id], 5)
        self.assertEqual(counts[b.id], 5)

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("Q", "1"))
    def test_every_selected_topic_keeps_at_least_one_slot(self, mock_gen):
        # Even a topic scheduled far into the future keeps its variety-floor
        # slot, so a full deck never silently drops a selected topic.
        due = self._topic("Due")
        far = self._topic("Far")
        self._review(due, self.today)
        self._review(far, self.today + datetime.timedelta(days=365))
        problems = _generate_problems(self.user, 10, self.today)
        counts = Counter(p["topic_id"] for p in problems)
        self.assertGreaterEqual(counts[far.id], 1)
        self.assertEqual(sum(counts.values()), 10)


class GradeTopicTests(TestCase):
    """Applying answer outcomes to the SM-2 schedule (the once-per-day rule)."""

    def setUp(self):
        self.user = make_user()
        self.course = make_course()
        self.today = datetime.date(2026, 7, 21)
        self.topic = make_topic(self.course, generator_name="addition")
        select(self.user, self.topic)

    def _review(self):
        return TopicReview.objects.get(user=self.user, topic=self.topic)

    def test_first_correct_answer_creates_review_due_in_the_future(self):
        _grade_topic(self.user, self.topic.id, "correct_first", self.today)
        review = self._review()
        # First success: interval 1 day, so due tomorrow.
        self.assertEqual(review.interval, 1)
        self.assertEqual(review.due_date, self.today + datetime.timedelta(days=1))
        self.assertEqual(review.repetitions, 1)

    def test_wrong_answer_schedules_for_tomorrow(self):
        _grade_topic(self.user, self.topic.id, "incorrect", self.today)
        review = self._review()
        self.assertEqual(review.interval, 1)
        self.assertEqual(review.repetitions, 0)
        self.assertEqual(review.due_date, self.today + datetime.timedelta(days=1))

    def test_unknown_outcome_is_ignored(self):
        _grade_topic(self.user, self.topic.id, "bogus", self.today)
        self.assertFalse(TopicReview.objects.filter(user=self.user, topic=self.topic).exists())

    def test_grade_records_one_daily_grade_row(self):
        _grade_topic(self.user, self.topic.id, "correct_first", self.today)
        self.assertEqual(
            DailyTopicGrade.objects.filter(
                user=self.user, topic=self.topic, date=self.today
            ).count(),
            1,
        )

    def test_repeat_success_does_not_raise_schedule(self):
        # Mature topic; a passing repeat the same day must not lengthen the interval.
        TopicReview.objects.update_or_create(
            user=self.user, topic=self.topic,
            defaults={"ease": 2.5, "interval": 10, "repetitions": 3,
                      "due_date": self.today},
        )
        _grade_topic(self.user, self.topic.id, "correct_first", self.today)  # first
        after_first = self._review().due_date
        _grade_topic(self.user, self.topic.id, "correct_first", self.today)  # repeat
        self.assertEqual(self._review().due_date, after_first)

    def test_repeat_miss_pulls_schedule_down(self):
        # First answer correct (long interval), then a repeat miss collapses it.
        TopicReview.objects.update_or_create(
            user=self.user, topic=self.topic,
            defaults={"ease": 2.5, "interval": 10, "repetitions": 3,
                      "due_date": self.today},
        )
        _grade_topic(self.user, self.topic.id, "correct_first", self.today)
        self.assertGreater(self._review().interval, 1)
        _grade_topic(self.user, self.topic.id, "incorrect", self.today)
        self.assertEqual(self._review().interval, 1)  # lapsed by the repeat

    def test_repeated_misses_do_not_compound_from_snapshot(self):
        # Two misses in a day must equal one miss — recomputed from the snapshot,
        # not applied twice (which would drop ease twice).
        TopicReview.objects.update_or_create(
            user=self.user, topic=self.topic,
            defaults={"ease": 2.5, "interval": 10, "repetitions": 3,
                      "due_date": self.today},
        )
        _grade_topic(self.user, self.topic.id, "incorrect", self.today)
        ease_after_one = self._review().ease
        _grade_topic(self.user, self.topic.id, "incorrect", self.today)
        self.assertEqual(self._review().ease, ease_after_one)

    def test_second_attempt_grades_lower_than_first(self):
        # correct_second (q=3) yields a lower ease than correct_first (q=5).
        other = make_topic(self.course, topic_name="Other", generator_name="addition")
        select(self.user, other)
        _grade_topic(self.user, self.topic.id, "correct_first", self.today)
        _grade_topic(self.user, other.id, "correct_second", self.today)
        first = TopicReview.objects.get(user=self.user, topic=self.topic)
        second = TopicReview.objects.get(user=self.user, topic=other)
        self.assertGreater(first.ease, second.ease)


class AdvanceGradingTests(TestCase):
    """The advance endpoint grading the card being left."""

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)
        self.course = make_course()
        self.topic = make_topic(self.course, generator_name="addition")
        select(self.user, self.topic)
        Settings.objects.update_or_create(
            user=self.user, defaults={"questions_per_day": 3}
        )

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_advance_with_outcome_grades_the_current_card(self, mock_gen):
        self.client.get("/deck/?today=2026-07-21")
        self.client.post(
            "/deck/advance/?today=2026-07-21",
            data=json.dumps({"outcome": "correct_first"}),
            content_type="application/json",
        )
        review = TopicReview.objects.get(user=self.user, topic=self.topic)
        self.assertEqual(review.due_date, datetime.date(2026, 7, 22))

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_advance_without_body_does_not_grade(self, mock_gen):
        self.client.get("/deck/?today=2026-07-21")
        self.client.post("/deck/advance/?today=2026-07-21")
        self.assertFalse(TopicReview.objects.filter(user=self.user).exists())

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_stray_advance_on_new_day_does_not_grade(self, mock_gen):
        # No deck exists yet for the new day: the advance builds one at index 0
        # and must not grade (nothing was answered).
        self.client.post(
            "/deck/advance/?today=2026-07-21",
            data=json.dumps({"outcome": "correct_first"}),
            content_type="application/json",
        )
        self.assertFalse(TopicReview.objects.filter(user=self.user).exists())


class PruneOrphanedTopicsTests(TestCase):
    """The 0010 migration must delete topics no longer in the seed and purge
    their frozen cards from cached decks, keeping the student on the same
    remaining card. A topic removed from the seed used to linger in the DB,
    still selected and still served from cached decks — that's how untypeable
    matrix/complex answers kept surfacing, and how a user with only removed
    topics selected still saw cards while the Courses page showed nothing."""

    def setUp(self):
        self.user = make_user()
        self.course = make_course()

    def test_orphaned_topic_and_its_cards_are_removed(self):
        # `addition` is in the seed (valid); a made-up name is not (orphaned).
        valid = make_topic(self.course, topic_name="Addition of two numbers",
                            generator_name="addition")
        orphan = make_topic(self.course, topic_name="Old Matrix Topic",
                            generator_name="matrix_multiplication_removed")
        select(self.user, valid)
        select(self.user, orphan)

        # A cached deck interleaving valid and orphaned cards, cursor at index 2.
        DailyDeck.objects.create(
            user=self.user,
            date=datetime.date(2026, 7, 22),
            current_index=2,
            problems=[
                {"problem": "v0", "solution": "1", "topic_id": valid.id},
                {"problem": "orphan1", "solution": r"\begin{bmatrix}1\end{bmatrix}",
                 "topic_id": orphan.id},
                {"problem": "v1", "solution": "2", "topic_id": valid.id},
                {"problem": "orphan2", "solution": r"\frac{1}{2}", "topic_id": orphan.id},
            ],
        )

        from django.apps import apps
        import importlib
        migration = importlib.import_module(
            "myapp.migrations.0010_prune_orphaned_topics"
        )
        migration.prune_orphaned_topics(apps, None)

        # Orphaned topic and its selection are gone; valid topic remains.
        self.assertFalse(Topic.objects.filter(id=orphan.id).exists())
        self.assertTrue(Topic.objects.filter(id=valid.id).exists())
        self.assertFalse(
            UserTopicSelection.objects.filter(topic_id=orphan.id).exists()
        )

        # The cached deck keeps only the valid cards, and the cursor shifts back
        # by the one orphaned card that sat before it (index 2 -> 1).
        deck = DailyDeck.objects.get(user=self.user)
        self.assertEqual([p["problem"] for p in deck.problems], ["v0", "v1"])
        self.assertEqual(deck.current_index, 1)
