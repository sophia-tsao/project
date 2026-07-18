from django.shortcuts import render
from django.http import HttpResponse
from .models import Course, Topic, Settings, DailyDeck
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from mathgenerator import gen_by_name
import random
import json

def index(request):
    return render(request, "myapp/index.html")
def view_courses(request):
    courses=list(Course.objects.all().values())
    return JsonResponse({"courses":courses})
def view_course_topics(request, courseID):
    # Returns topics for specific course
    topics = list(Course.objects.get(id=courseID).topics.all().values())
    return JsonResponse({"topics":topics})
@csrf_exempt
@require_http_methods(["PATCH"])
def toggle_topic(request, topicID):
    try:
        topic = Topic.objects.get(id=topicID)
    except Topic.DoesNotExist:
        return JsonResponse({"error": "Topic not found"}, status=404)
    body = json.loads(request.body)
    topic.is_selected = body["is_selected"]
    topic.save(update_fields=["is_selected"])
    if topic.course:
        all_selected = not topic.course.topics.filter(is_selected=False).exists()
        topic.course.is_selected = all_selected
        topic.course.save(update_fields=["is_selected"])
    return JsonResponse({"id": topic.id, "is_selected": topic.is_selected})

@csrf_exempt
@require_http_methods(["PATCH"])
def set_course_topics_selected(request, courseID):
    try:
        course = Course.objects.get(id=courseID)
    except Course.DoesNotExist:
        return JsonResponse({"error": "Course not found"}, status=404)
    body = json.loads(request.body)
    new_value = body["is_selected"]
    course.topics.all().update(is_selected=new_value)
    course.is_selected = new_value
    course.save(update_fields=["is_selected"])
    return JsonResponse({"course_id": courseID, "is_selected": new_value})

def _make_problem():
    """Generate a single problem from the currently selected topics.

    Returns a dict with 'problem' and 'solution', or None if no topics are
    selected.
    """
    generators = list(
        Topic.objects.filter(is_selected=True)
        .exclude(generator_name__isnull=True)
        .values_list("generator_name", flat=True)
    )
    if not generators:
        return None
    name = random.choice(generators)
    problem, solution = gen_by_name(name)

    sol_str = str(solution).strip().replace('$', '').strip()
    try:
        sol_float = float(sol_str)
        if '.' in sol_str:
            rounded = round(sol_float, 3)
            rounded_str = str(rounded)
            if rounded_str != sol_str:
                problem = problem.rstrip() + " Round to the nearest thousandth if necessary."
            solution = rounded_str
    except (ValueError, TypeError):
        pass

    return {"problem": problem, "solution": str(solution)}


def generate_problem(request):
    result = _make_problem()
    if result is None:
        return JsonResponse({"no_topics": True})
    return JsonResponse(result)


def _serialize_settings(settings):
    return {"language": settings.language, "questions_per_day": settings.questions_per_day}


@csrf_exempt
@require_http_methods(["GET", "PATCH"])
def settings_view(request):
    settings = Settings.load()
    if request.method == "PATCH":
        body = json.loads(request.body)
        if "language" in body:
            settings.language = body["language"]
        if "questions_per_day" in body:
            try:
                count = int(body["questions_per_day"])
            except (ValueError, TypeError):
                return JsonResponse({"error": "questions_per_day must be an integer"}, status=400)
            if count < 1:
                return JsonResponse({"error": "questions_per_day must be at least 1"}, status=400)
            settings.questions_per_day = count
        settings.save()
    return JsonResponse(_serialize_settings(settings))


def _build_deck(count):
    """Generate up to `count` problems. Returns a list (possibly empty)."""
    problems = []
    for _ in range(count):
        problem = _make_problem()
        if problem is None:
            break
        problems.append(problem)
    return problems


def _get_or_create_today_deck():
    """Return today's deck, creating a fresh one if none exists for today.

    Any deck from a previous day is discarded so a new day yields new problems.
    """
    today = timezone.localdate()
    deck = DailyDeck.objects.filter(date=today).first()
    if deck is None:
        # A new day: clear out stale decks and build a fresh one.
        DailyDeck.objects.exclude(date=today).delete()
        settings = Settings.load()
        problems = _build_deck(settings.questions_per_day)
        deck = DailyDeck.objects.create(date=today, problems=problems, current_index=0)
    return deck


def _deck_payload(deck):
    total = len(deck.problems)
    if total == 0:
        return {"no_topics": True}
    if deck.current_index >= total:
        return {"completed": True, "total": total}
    current = deck.problems[deck.current_index]
    return {
        "problem": current["problem"],
        "solution": current["solution"],
        "current_number": deck.current_index + 1,
        "total": total,
    }


@csrf_exempt
@require_http_methods(["GET"])
def get_deck(request):
    deck = _get_or_create_today_deck()
    return JsonResponse(_deck_payload(deck))


@csrf_exempt
@require_http_methods(["POST"])
def advance_deck(request):
    """Move to the next problem in today's deck."""
    deck = _get_or_create_today_deck()
    if deck.current_index < len(deck.problems):
        deck.current_index += 1
        deck.save(update_fields=["current_index"])
    return JsonResponse(_deck_payload(deck))
