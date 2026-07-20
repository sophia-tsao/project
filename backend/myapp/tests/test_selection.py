"""Tests for course/topic listing and per-user topic selection."""
import json
from unittest import mock

from django.test import TestCase, Client

from myapp.models import UserTopicSelection, Settings, DailyDeck
from .factories import make_user, make_course, make_topic, select


class ViewCoursesTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)
        self.course = make_course()
        self.t1 = make_topic(self.course, topic_name="Linear")
        self.t2 = make_topic(self.course, topic_name="Quadratic")

    def test_course_selected_only_when_all_topics_selected(self):
        select(self.user, self.t1)
        courses = self.client.get("/courses/").json()["courses"]
        self.assertFalse(courses[0]["is_selected"])

        select(self.user, self.t2)
        courses = self.client.get("/courses/").json()["courses"]
        self.assertTrue(courses[0]["is_selected"])

    def test_course_with_no_topics_is_not_selected(self):
        empty = make_course(course_name="Empty", grade_level=5)
        courses = {c["id"]: c for c in self.client.get("/courses/").json()["courses"]}
        self.assertFalse(courses[empty.id]["is_selected"])


class ViewCourseTopicsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)
        self.course = make_course()
        self.topic = make_topic(self.course, topic_name="Derivatives")

    def test_topics_include_selection_state(self):
        select(self.user, self.topic)
        data = self.client.get(f"/courses/{self.course.id}/topics").json()
        self.assertIn("is_selected", data["topics"][0])
        self.assertTrue(data["topics"][0]["is_selected"])

    def test_selection_is_per_user(self):
        other = make_user()
        select(other, self.topic)
        # Current user has not selected it, so it reads as unselected.
        data = self.client.get(f"/courses/{self.course.id}/topics").json()
        self.assertFalse(data["topics"][0]["is_selected"])


class ToggleTopicTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)
        self.course = make_course()
        self.topic = make_topic(self.course)

    def _toggle(self, topic_id, is_selected):
        return self.client.patch(
            f"/topics/{topic_id}/select",
            data=json.dumps({"is_selected": is_selected}),
            content_type="application/json",
        )

    def test_select_topic(self):
        response = self._toggle(self.topic.id, True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_selected"])
        self.assertTrue(
            UserTopicSelection.objects.filter(user=self.user, topic=self.topic).exists()
        )

    def test_select_is_idempotent(self):
        self._toggle(self.topic.id, True)
        self._toggle(self.topic.id, True)
        self.assertEqual(
            UserTopicSelection.objects.filter(user=self.user, topic=self.topic).count(), 1
        )

    def test_deselect_topic(self):
        select(self.user, self.topic)
        response = self._toggle(self.topic.id, False)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            UserTopicSelection.objects.filter(user=self.user, topic=self.topic).exists()
        )

    def test_toggle_nonexistent_topic(self):
        response = self._toggle(99999, True)
        self.assertEqual(response.status_code, 404)


class SetCourseTopicsSelectedTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)
        self.course = make_course(course_name="Geometry", grade_level=9)
        self.t1 = make_topic(self.course, topic_name="Triangles")
        self.t2 = make_topic(self.course, topic_name="Circles")

    def _set(self, course_id, is_selected):
        return self.client.patch(
            f"/courses/{course_id}/select",
            data=json.dumps({"is_selected": is_selected}),
            content_type="application/json",
        )

    def test_select_all(self):
        response = self._set(self.course.id, True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            UserTopicSelection.objects.filter(user=self.user).count(), 2
        )

    def test_select_all_is_idempotent(self):
        select(self.user, self.t1)
        response = self._set(self.course.id, True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            UserTopicSelection.objects.filter(user=self.user).count(), 2
        )

    def test_deselect_all(self):
        select(self.user, self.t1)
        select(self.user, self.t2)
        response = self._set(self.course.id, False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            UserTopicSelection.objects.filter(user=self.user).count(), 0
        )

    def test_nonexistent_course(self):
        response = self._set(99999, True)
        self.assertEqual(response.status_code, 404)


class TopicToggleDeckRegenerationTests(TestCase):
    """Toggling a topic regenerates today's unanswered cards immediately.

    Two topics use distinct generators so a regenerated tail is recognisable
    by which generator produced its problems.
    """

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)
        self.course = make_course()
        self.add_topic = make_topic(self.course, generator_name="addition")
        self.sub_topic = make_topic(self.course, generator_name="subtraction")
        Settings.objects.update_or_create(
            user=self.user, defaults={"questions_per_day": 4}
        )

    def _toggle(self, topic_id, is_selected):
        return self.client.patch(
            f"/topics/{topic_id}/select",
            data=json.dumps({"is_selected": is_selected}),
            content_type="application/json",
        )

    @mock.patch("myapp.views.mathgenerator.subtraction", return_value=("$9-1=$", "$8$"))
    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_selecting_topic_builds_tail_from_new_set(self, mock_add, mock_sub):
        # Deck starts built from addition only.
        select(self.user, self.add_topic)
        self.client.get("/deck/")
        deck = DailyDeck.objects.get(user=self.user)
        self.assertTrue(all(p["solution"] == "2" for p in deck.problems))

        # Advance one, then add subtraction: the unanswered tail is regenerated
        # and can now include subtraction problems.
        self.client.post("/deck/advance/")
        self._toggle(self.sub_topic.id, True)

        deck.refresh_from_db()
        self.assertEqual(len(deck.problems), 4)  # total preserved
        self.assertEqual(deck.current_index, 1)  # progress preserved
        self.assertEqual(deck.problems[0]["solution"], "2")  # answered card kept

    @mock.patch("myapp.views.mathgenerator.subtraction", return_value=("$9-1=$", "$8$"))
    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_deselecting_topic_purges_it_from_unanswered_tail(self, mock_add, mock_sub):
        select(self.user, self.add_topic)
        select(self.user, self.sub_topic)
        self.client.get("/deck/")

        # Remove subtraction; the regenerated tail must contain only addition.
        self._toggle(self.sub_topic.id, False)

        deck = DailyDeck.objects.get(user=self.user)
        self.assertEqual(len(deck.problems), 4)
        self.assertTrue(all(p["solution"] == "2" for p in deck.problems))

    @mock.patch("myapp.views.mathgenerator.subtraction", return_value=("$9-1=$", "$8$"))
    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_swapping_courses_via_transient_empty_state_keeps_full_deck(
        self, mock_add, mock_sub
    ):
        # A student works a few cards, then swaps their entire topic set:
        # deselect the old topic (leaving nothing selected) then select a new
        # one. The transient no-topics state must not strand them on a short,
        # already-"finished" deck. Regression for the "finished all 4" bug.
        select(self.user, self.add_topic)
        self.client.get("/deck/")  # 4-card deck (questions_per_day=4)
        self.client.post("/deck/advance/")
        self.client.post("/deck/advance/")  # answered 2

        self._toggle(self.add_topic.id, False)  # now nothing selected
        deck = DailyDeck.objects.get(user=self.user)
        # Tail can't be generated, but the deck isn't permanently shrunk below
        # what a later reselection can refill.
        self.assertEqual(deck.current_index, 2)

        self._toggle(self.sub_topic.id, True)  # pick the new topic

        deck.refresh_from_db()
        self.assertEqual(len(deck.problems), 4)  # refilled to target
        self.assertEqual(deck.current_index, 2)  # progress preserved
        data = self.client.get("/deck/").json()
        self.assertFalse(data.get("completed"))
        self.assertEqual(data["current_number"], 3)
        self.assertEqual(data["total"], 4)

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_no_deck_yet_is_a_noop(self, mock_add):
        # No deck for today: toggling shouldn't create one.
        self._toggle(self.add_topic.id, True)
        self.assertFalse(DailyDeck.objects.filter(user=self.user).exists())

    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_finished_deck_is_left_alone(self, mock_add):
        select(self.user, self.add_topic)
        self.client.get("/deck/")
        for _ in range(4):
            self.client.post("/deck/advance/")  # finish the deck
        deck = DailyDeck.objects.get(user=self.user)
        self.assertEqual(deck.current_index, 4)

        self._toggle(self.sub_topic.id, True)

        deck.refresh_from_db()
        self.assertEqual(deck.current_index, 4)
        self.assertEqual(len(deck.problems), 4)

    @mock.patch("myapp.views.mathgenerator.subtraction", return_value=("$9-1=$", "$8$"))
    @mock.patch("myapp.views.mathgenerator.addition", return_value=("$1+1=$", "$2$"))
    def test_course_level_toggle_regenerates_tail(self, mock_add, mock_sub):
        select(self.user, self.add_topic)
        self.client.get("/deck/")
        self.client.post("/deck/advance/")

        # Select the whole course (adds subtraction).
        self.client.patch(
            f"/courses/{self.course.id}/select",
            data=json.dumps({"is_selected": True}),
            content_type="application/json",
        )

        deck = DailyDeck.objects.get(user=self.user)
        self.assertEqual(len(deck.problems), 4)
        self.assertEqual(deck.current_index, 1)
