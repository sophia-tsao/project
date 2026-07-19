"""Tests for problem generation and the daily deck lifecycle.

The `addition` generator (which the test topics use) is mocked so problem
text/solutions are deterministic and the rounding logic can be asserted
precisely.
"""
import datetime
from unittest import mock

from django.test import TestCase, Client

from myapp.models import DailyDeck, Settings
from myapp import views
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
