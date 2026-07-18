from django.db import models

# Create your models here.

class Course(models.Model):
    course_name = models.CharField()
    grade_level = models.IntegerField()
    is_selected = models.BooleanField(default=False)

    def __str__(self):
        return self.course_name

class Topic(models.Model):
    topic_name = models.CharField()
    course = models.ForeignKey('Course', blank=True, null=True, on_delete=models.SET_NULL, related_name="topics")
    is_selected = models.BooleanField(default=False)
    generator_name = models.CharField(blank=True, null=True)

    def __str__(self):
        return self.topic_name

class Settings(models.Model):
    """Global, single-row user settings."""
    language = models.CharField(default='en', max_length=10)
    questions_per_day = models.IntegerField(default=10)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        # Enforce a single settings row.
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return "Settings"

class DailyDeck(models.Model):
    """A set of problems generated for a single day."""
    date = models.DateField(unique=True)
    problems = models.JSONField(default=list)
    current_index = models.IntegerField(default=0)

    def __str__(self):
        return f"Deck {self.date} ({self.current_index}/{len(self.problems)})"
