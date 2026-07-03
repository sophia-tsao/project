from django.contrib import admin
from .models import Course, Topic


class TopicInline(admin.TabularInline):
    model = Topic
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    inlines = [TopicInline]


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("topic_name", "course")
    list_filter = ("course",)