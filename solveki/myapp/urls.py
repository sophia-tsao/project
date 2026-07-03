from django.urls import path
from . import views
urlpatterns = [
    path('', views.index, name="index"),
    path('problem/', views.generate_problem, name="generate_problem"),
    path('courses/', views.view_courses, name="view_courses"),
    path('courses/<int:courseID>/topics', views.view_course_topics, name="view_course_topics")
]