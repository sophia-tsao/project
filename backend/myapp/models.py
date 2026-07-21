from django.db import models
from django.conf import settings as django_settings

# Create your models here.

class Course(models.Model):
    course_name = models.CharField()
    grade_level = models.IntegerField()

    def __str__(self):
        return self.course_name

class Topic(models.Model):
    topic_name = models.CharField()
    course = models.ForeignKey('Course', blank=True, null=True, on_delete=models.SET_NULL, related_name="topics")
    generator_name = models.CharField(blank=True, null=True)

    def __str__(self):
        return self.topic_name

class UserTopicSelection(models.Model):
    """Records that a given user has selected a given topic.

    Topic selection is per-user, so it lives here rather than as a flag on the
    shared Topic catalog. A row's existence means "selected"; no row means
    "not selected".
    """
    user = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="topic_selections")
    topic = models.ForeignKey('Topic', on_delete=models.CASCADE, related_name="selections")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "topic"], name="unique_user_topic"),
        ]

    def __str__(self):
        return f"{self.user} -> {self.topic}"

class TopicReview(models.Model):
    """Spaced-repetition (SM-2) scheduling state for one user's practice of one topic.

    Solveki schedules *topics*, not individual problems: every problem is freshly
    generated, so the schedulable unit is the user's mastery of a topic. One row
    per (user, topic) holds the SM-2 state used to decide when the topic is next
    due for review.

    Separate from `UserTopicSelection` on purpose: selection and learning history
    have independent lifecycles, so deselecting a topic (dropping the selection
    row) preserves its review state for when it's selected again.

    `due_date` is null until the topic has been reviewed at least once; a null
    `due_date` means "due now" (never practiced yet).
    """
    user = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="topic_reviews")
    topic = models.ForeignKey('Topic', on_delete=models.CASCADE, related_name="reviews")
    ease = models.FloatField(default=2.5)
    interval = models.IntegerField(default=0)  # days until next review
    repetitions = models.IntegerField(default=0)  # consecutive successful reviews
    due_date = models.DateField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "topic"], name="unique_user_topic_review"),
        ]

    def __str__(self):
        return f"Review({self.user} -> {self.topic}, due {self.due_date})"

class Settings(models.Model):
    """Per-user settings."""
    user = models.OneToOneField(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="settings")
    language = models.CharField(default='en', max_length=10)
    questions_per_day = models.IntegerField(default=10)

    @classmethod
    def load(cls, user):
        obj, _ = cls.objects.get_or_create(user=user)
        return obj

    def __str__(self):
        return f"Settings({self.user})"

class DailyDeck(models.Model):
    """A set of problems generated for a single day, for a single user."""
    user = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="decks")
    date = models.DateField()
    problems = models.JSONField(default=list)
    current_index = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "date"], name="unique_user_date_deck"),
        ]

    def __str__(self):
        return f"Deck {self.user} {self.date} ({self.current_index}/{len(self.problems)})"
