from django.shortcuts import render
from django.http import HttpResponse
from .models import Course, Topic
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from mathgenerator import gen_by_name
import random
import json

TOPIC_TO_GENERATOR = {
    "Addition of two numbers": "addition",
    "Subtraction of two numbers": "subtraction",
    "Convert minutes to hours and minutes": "minutes_to_hours",
    "Multiplication": "multiplication",
    "Division": "division",
    "Perimeter of Polygons": "perimeter_of_polygons",
    "Compare Fractions": "compare_fractions",
    "Fraction to Decimal": "fraction_to_decimal",
    "Is Prime": "is_prime",
    "Is Composite": "is_composite",
    "Factors of a number": "factors",
    "Fraction Multiplication": "fraction_multiplication",
    "Divide Fractions": "divide_fractions",
    "Volume of a cube": "volume_cube",
    "Volume of a cuboid": "volume_cuboid",
    "Absolute difference between two numbers": "absolute_difference",
    "Exponentiation": "exponentiation",
    "Square": "square",
    "Percentage of a number": "percentage",
    "Greatest Common Divisor of N Numbers ( GCD / HCF )": "greatest_common_divisor",
    "LCM (Least Common Multiple)": "lcm",
    "Prime Factors": "prime_factors",
    "Common Factors": "common_factors",
    "Combine Like Terms": "combine_like_terms",
    "Area of Triangle": "area_of_triangle",
    "Area of Trapezoid": "area_of_trapezoid",
    "Surface area of a cube": "surface_area_cube",
    "Surface area of a cuboid": "surface_area_cuboid",
    "Mean and Median": "mean_median",
    "Basic Algebra": "basic_algebra",
    "Complementary and Supplementary Angle": "complementary_and_supplementary_angle",
    "Third Angle of Triangle": "third_angle_of_triangle",
    "Fourth Angle of Quadrilateral": "fourth_angle_of_quadrilateral",
    "Area of Circle": "area_of_circle",
    "Circumference of Circle": "circumference",
    "Area of Circle given center and a point on circle": "area_of_circle_given_center_and_point",
    "Surface area of a cone": "surface_area_cone",
    "Surface area of a cylinder": "surface_area_cylinder",
    "Curved surface area of a cylinder": "curved_surface_area_cylinder",
    "Surface area of a pyramid": "surface_area_pyramid",
    "Simple Interest": "simple_interest",
    "Profit or Loss Percent": "profit_loss_percent",
    "Celsius to Fahrenheit": "celsius_to_fahrenheit",
    "Percentage difference between two numbers": "percentage_difference",
    "Percentage error": "percentage_error",
    "Probability of a certain sum appearing on faces of dice": "dice_sum_probability",
    "Square Root": "square_root",
    "Cube Root": "cube_root",
    "Product of scientific notations": "product_of_scientific_notations",
    "Pythagorean Theorem": "pythagorean_theorem",
    "Volume of a cylinder": "volume_cylinder",
    "Volume of a cone": "volume_cone",
    "Volume of a sphere": "volume_sphere",
    "Volume of a hemisphere": "volume_hemisphere",
    "Surface area of a sphere": "surface_area_sphere",
    "Solve a System of Equations in R^2": "system_of_equations",
    "Linear Equations": "linear_equations",
    "Simplify Square Root": "simplify_square_root",
    "Power of Powers": "power_of_powers",
    "Quotient of Powers with Same Base": "quotient_of_power_same_base",
    "Quotient of Powers with Same Power": "quotient_of_power_same_power",
    "Comparing Surds": "surds_comparison",
    "Expanding Factored Binomial": "expanding",
    "Factoring Quadratic": "factoring",
    "Quadratic Equation": "quadratic_equation",
    "Intersection of two lines": "intersection_of_two_lines",
    "Equation of Line from Two Points": "equation_of_line_from_two_points",
    "Equation of line from two points": "line_equation_from_2_points",
    "Compound Interest": "compound_interest",
    "Arithmetic Progression Sum": "arithmetic_progression_sum",
    "Arithmetic Progression Term": "arithmetic_progression_term",
    "Geometric Progression": "geometric_progression",
    "Mean, Standard Deviation and Variance": "data_summary",
    "Distance between 2 points": "distance_two_points",
    "Midpoint of two points": "midpoint_of_two_points",
    "Trigonometric Values": "basic_trigonometry",
    "Arc length of Angle": "arc_length",
    "Area of a Sector": "sector_area",
    "Degrees to Radians": "degree_to_rad",
    "Radians to Degrees": "radian_to_deg",
    "Sum of Angles of Polygon": "sum_of_polygon_angles",
    "Angle of a Regular Polygon": "angle_regular_polygon",
    "Valid Triangle": "valid_triangle",
    "Volume of a pyramid": "volume_pyramid",
    "Volume of the frustum of a cone": "volume_cone_frustum",
    "Logarithm": "log",
    "Complex Quadratic Equation": "complex_quadratic",
    "Multiplication of 2 complex numbers": "multiply_complex_numbers",
    "Determinant to 2x2 Matrix": "int_matrix_22_determinant",
    "Multiply Two Matrices": "matrix_multiplication",
    "Multiply Integer to 2x2 Matrix": "multiply_int_to_22_matrix",
    "Invert Matrix": "invert_matrix",
    "Factorial": "factorial",
    "Union, Intersection, Difference of Two Sets": "set_operation",
    "Combinations of Objects": "combinations",
    "Permutations": "permutation",
    "Conditional Probability": "conditional_probability",
    "Binomial distribution": "binomial_distribution",
    "Confidence interval For sample S": "confidence_interval",
    "Angle between 2 vectors": "angle_btw_vectors",
    "Dot product of 2 vectors": "vector_dot",
    "Cross product of 2 vectors": "vector_cross",
    "Orthogonal Projection": "orthogonal_projection",
    "Euclidian norm or L2 norm of a vector": "euclidian_norm",
    "Complex to polar form": "complex_to_polar",
    "Power Rule Differentiation": "power_rule_differentiation",
    "Power Rule Integration": "power_rule_integration",
    "Definite Integral of Quadratic Equation": "definite_integral",
    "Stationary Points": "stationary_points",
    "Trigonometric Differentiation": "trig_differentiation",
}

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

def generate_problem(request):
    selected_topics = Topic.objects.filter(is_selected=True).values_list("topic_name", flat=True)
    generators = [TOPIC_TO_GENERATOR[t] for t in selected_topics if t in TOPIC_TO_GENERATOR]
    if not generators:
        return JsonResponse({"no_topics": True})
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

    return JsonResponse({"problem": problem, "solution": str(solution)})