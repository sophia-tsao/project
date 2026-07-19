"""Tests for the per-user settings endpoint."""
import json
from unittest import mock

from django.test import TestCase, Client
from django.utils import timezone

from myapp.models import Settings, DailyDeck
from .factories import make_user, make_course, make_topic, select


class SettingsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)

    def _patch(self, body):
        return self.client.patch(
            "/settings/", data=json.dumps(body), content_type="application/json"
        )

    def test_get_creates_defaults(self):
        response = self.client.get("/settings/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["language"], "en")
        self.assertEqual(data["questions_per_day"], 10)

    def test_update_language_and_count(self):
        response = self._patch({"language": "es", "questions_per_day": 5})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["language"], "es")
        self.assertEqual(data["questions_per_day"], 5)
        settings = Settings.load(self.user)
        self.assertEqual(settings.questions_per_day, 5)

    def test_questions_per_day_must_be_integer(self):
        response = self._patch({"questions_per_day": "lots"})
        self.assertEqual(response.status_code, 400)

    def test_questions_per_day_must_be_positive(self):
        response = self._patch({"questions_per_day": 0})
        self.assertEqual(response.status_code, 400)

    def test_partial_update_leaves_other_fields(self):
        self._patch({"language": "fr", "questions_per_day": 7})
        self._patch({"language": "de"})
        settings = Settings.load(self.user)
        self.assertEqual(settings.language, "de")
        self.assertEqual(settings.questions_per_day, 7)


class SettingsDeckResizeTests(TestCase):
    """Saving a new card count resizes today's deck immediately (grow only)."""

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)
        self.course = make_course()
        self.topic = make_topic(self.course, generator_name="addition")
        select(self.user, self.topic)
        Settings.objects.update_or_create(
            user=self.user, defaults={"questions_per_day": 10}
        )

    def _patch(self, body):
        return self.client.patch(
            "/settings/", data=json.dumps(body), content_type="application/json"
        )

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_increasing_count_grows_todays_deck(self, mock_gen):
        # Build today's deck at the current count of 10.
        self.assertEqual(self.client.get("/deck/").json()["total"], 10)

        self._patch({"questions_per_day": 15})

        deck = DailyDeck.objects.get(user=self.user)
        self.assertEqual(len(deck.problems), 15)
        self.assertEqual(self.client.get("/deck/").json()["total"], 15)

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_growth_preserves_progress(self, mock_gen):
        self.client.get("/deck/")  # build deck at 10
        self.client.post("/deck/advance/")
        self.client.post("/deck/advance/")  # now on problem 3 of 10

        self._patch({"questions_per_day": 15})

        deck = DailyDeck.objects.get(user=self.user)
        self.assertEqual(len(deck.problems), 15)
        self.assertEqual(deck.current_index, 2)  # progress untouched
        self.assertEqual(self.client.get("/deck/").json()["current_number"], 3)

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_decreasing_count_leaves_todays_deck_untouched(self, mock_gen):
        self.client.get("/deck/")  # build deck at 10

        self._patch({"questions_per_day": 5})

        deck = DailyDeck.objects.get(user=self.user)
        self.assertEqual(len(deck.problems), 10)  # not shrunk today
        self.assertEqual(deck.current_index, 0)

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_no_deck_yet_is_a_noop(self, mock_gen):
        # No deck built for today; saving should not create one.
        self._patch({"questions_per_day": 15})
        self.assertFalse(DailyDeck.objects.filter(user=self.user).exists())
