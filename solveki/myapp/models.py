from django.db import models

# Create your models here.

class Course(models.Model):
    course_name = models.CharField()
    grade_level = models.IntegerField()

    def __str__(self):
        return self.course_name

class Topic(models.Model):
    topic_name = models.CharField()
    course = models.ForeignKey('Course', blank=True, null=True, on_delete=models.SET_NULL, related_name="topics")

    def __str__(self):
        return self.topic_name
