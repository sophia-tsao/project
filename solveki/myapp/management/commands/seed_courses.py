from django.core.management.base import BaseCommand
from myapp.models import Course, Topic

CURRICULUM = [
    ("Grade 1", 1, [
        "Addition of two numbers",
        "Subtraction of two numbers",
    ]),
    ("Grade 2", 2, [
        "Convert minutes to hours and minutes",
    ]),
    ("Grade 3", 3, [
        "Multiplication",
        "Division",
        "Perimeter of Polygons",
    ]),
    ("Grade 4", 4, [
        "Compare Fractions",
        "Fraction to Decimal",
        "Is Prime",
        "Is Composite",
        "Factors of a number",
    ]),
    ("Grade 5", 5, [
        "Fraction Multiplication",
        "Divide Fractions",
        "Volume of a cube",
        "Volume of a cuboid",
    ]),
    ("Grade 6", 6, [
        "Absolute difference between two numbers",
        "Exponentiation",
        "Square",
        "Percentage of a number",
        "Greatest Common Divisor of N Numbers ( GCD / HCF )",
        "LCM (Least Common Multiple)",
        "Prime Factors",
        "Common Factors",
        "Combine Like Terms",
        "Area of Triangle",
        "Area of Trapezoid",
        "Surface area of a cube",
        "Surface area of a cuboid",
        "Mean and Median",
    ]),
    ("Grade 7", 7, [
        "Basic Algebra",
        "Complementary and Supplementary Angle",
        "Third Angle of Triangle",
        "Fourth Angle of Quadrilateral",
        "Area of Circle",
        "Circumference of Circle",
        "Area of Circle given center and a point on circle",
        "Surface area of a cone",
        "Surface area of a cylinder",
        "Curved surface area of a cylinder",
        "Surface area of a pyramid",
        "Simple Interest",
        "Profit or Loss Percent",
        "Celsius to Fahrenheit",
        "Percentage difference between two numbers",
        "Percentage error",
        "Probability of a certain sum appearing on faces of dice",
    ]),
    ("Grade 8", 8, [
        "Square Root",
        "Cube Root",
        "Product of scientific notations",
        "Pythagorean Theorem",
        "Volume of a cylinder",
        "Volume of a cone",
        "Volume of a sphere",
        "Volume of a hemisphere",
        "Surface area of a sphere",
        "Solve a System of Equations in R^2",
        "Linear Equations",
    ]),
    ("Algebra I", 9, [
        "Simplify Square Root",
        "Power of Powers",
        "Quotient of Powers with Same Base",
        "Quotient of Powers with Same Power",
        "Comparing Surds",
        "Expanding Factored Binomial",
        "Factoring Quadratic",
        "Quadratic Equation",
        "Vertex of a Quadratic in Vertex Form",
        "Intersection of two lines",
        "Equation of Line from Two Points",
        "Equation of line from two points",
        "Compound Interest",
        "Arithmetic Progression Sum",
        "Arithmetic Progression Term",
        "Geometric Progression",
    ]),
    ("Geometry", 10, [
        "Distance between 2 points",
        "Midpoint of two points",
        "Trigonometric Values",
        "Arc length of Angle",
        "Area of a Sector",
        "Degrees to Radians",
        "Radians to Degrees",
        "Sum of Angles of Polygon",
        "Angle of a Regular Polygon",
        "Valid Triangle",
        "Volume of a pyramid",
        "Volume of the frustum of a cone",
    ]),
    ("Algebra II", 11, [
        "Logarithm",
        "Complex Quadratic Equation",
        "Multiplication of 2 complex numbers",
        "Determinant to 2x2 Matrix",
        "Multiply Two Matrices",
        "Multiply Integer to 2x2 Matrix",
        "Invert Matrix",
        "Average Rate of Change over Interval",
        "Factorial",
        "Union, Intersection, Difference of Two Sets",
        "Combinations of Objects",
        "Permutations",
    ]),
    ("Statistical Reasoning", 12, [
        "Mean, Standard Deviation and Variance",
        "Conditional Probability",
        "Binomial distribution",
        "Confidence interval For sample S",
    ]),
    ("Pre-Calculus", 12, [
        "Angle Sum",
        "Angle between 2 vectors",
        "Dot product of 2 vectors",
        "Cross product of 2 vectors",
        "Orthogonal Projection",
        "Euclidian norm or L2 norm of a vector",
        "Complex to polar form",
    ]),
    ("AP Calculus", 12, [
        "Power Rule Differentiation",
        "Power Rule Integration",
        "Definite Integral of Quadratic Equation",
        "Stationary Points",
        "Trigonometric Differentiation",
    ]),
]


class Command(BaseCommand):
    help = "Seed Course objects and link existing Topics to their courses"

    def handle(self, *args, **options):
        courses_created = 0
        topics_linked = 0
        topics_missing = []

        for course_name, grade_level, topic_names in CURRICULUM:
            course, created = Course.objects.get_or_create(
                course_name=course_name,
                defaults={"grade_level": grade_level},
            )
            if created:
                courses_created += 1

            for name in topic_names:
                try:
                    topic = Topic.objects.get(topic_name=name)
                    topic.course = course
                    topic.save()
                    topics_linked += 1
                except Topic.DoesNotExist:
                    topics_missing.append(name)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {courses_created} course(s) created, {topics_linked} topic(s) linked."
            )
        )
        if topics_missing:
            self.stdout.write(
                self.style.WARNING(f"Topics not found: {topics_missing}")
            )
