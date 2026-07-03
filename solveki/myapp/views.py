from django.shortcuts import render
from django.http import HttpResponse
from .models import Course, Topic
from django.http import JsonResponse
from mathgenerator import gen_by_name, get_gen_list
import random
# Create your views here.

def index(request):
    return render(request, "myapp/index.html")
def view_courses(request):
    courses=list(Course.objects.all().values())
    return JsonResponse({"courses":courses})
def view_course_topics(request, courseID):
    # Returns topics for specific course
    topics = list(Course.objects.get(id=courseID).topics.all().values())
    return JsonResponse({"topics":topics})
def generate_problem(request):
    gen_list = get_gen_list()
    name, _ = random.choice(gen_list)
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

    return JsonResponse({"problem": problem, "solution": str(solution)})