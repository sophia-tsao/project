"""Solveki-local geometry / trigonometry generators."""
import random
from math import gcd

from ._registry import register


@register
def angle_sum():
    r"""Angle Sum

    Given sin/cos/tan of two acute angles from Pythagorean triples, find a
    trig function of their sum as a simplified fraction.
    """
    triples = [
        [3, 4, 5],
        [5, 12, 13],
        [7, 24, 25],
        [8, 15, 17],
        [9, 40, 41],
        [12, 35, 37],
        [20, 21, 29],
    ]
    functions = []
    fractions = []
    triangles = [random.choice(triples), random.choice(triples)]
    for i in range(2):
        functions.append(random.choice(["sin", "cos", "tan"]))
        if functions[i] == "sin":
            fractions.append(f"{triangles[i][0]}/{triangles[i][2]}")
        elif functions[i] == "cos":
            fractions.append(f"{triangles[i][1]}/{triangles[i][2]}")
        else:
            fractions.append(f"{triangles[i][0]}/{triangles[i][1]}")
    ans_func = random.choice(["sin", "cos"])
    if ans_func == "sin":
        numerator = triangles[0][0] * triangles[1][1] + triangles[1][0] * triangles[0][1]
        denominator = triangles[0][2] * triangles[1][2]
    else:
        numerator = triangles[0][1] * triangles[1][1] - triangles[0][0] * triangles[1][0]
        denominator = triangles[0][2] * triangles[1][2]
    g = gcd(numerator, denominator)
    numerator //= g
    denominator //= g
    ans = f"{int(numerator)}/{int(denominator)}"
    problem = (
        f"For positive acute angles A and B, it is known that "
        f"$\\{functions[0]} A = {fractions[0]}$ and $\\{functions[1]} B = {fractions[1]}$. "
        f"Find the value of $\\{ans_func}(A+B)$ in the simplest form as a fraction."
    )
    solution = f"${ans}$"
    return problem, solution
