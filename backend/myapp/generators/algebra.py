"""Solveki-local algebra generators."""
import random

from ._registry import register


@register
def vertex_form(min_val=-10, max_val=10, min_a=-5, max_a=5):
    r"""Vertex of a Quadratic in Vertex Form

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Find the coordinates of the vertex of $y=2(x-3)^2+4$ | $(3, 4)$ |
    """
    a = random.choice([i for i in range(min_a, max_a + 1) if i != 0])
    h = random.randint(min_val, max_val)
    k = random.randint(min_val, max_val)

    h_str = f"x{'+' if -h >= 0 else '-'}{abs(h)}" if h != 0 else "x"
    a_str = "" if a == 1 else ("-" if a == -1 else str(a))

    problem = f"Find the coordinates of the vertex of $y={a_str}({h_str})^2{'+' if k >= 0 else '-'}{abs(k)}$"
    solution = f"$({h}, {k})$"
    return problem, solution


@register
def aroc_over_interval(max_degree=5, max_coefficient=10, min_coefficient=-10):
    r"""Average Rate of Change over an Interval

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Given the function $2x^2+3$, find the average rate of change over the interval $1<=x<=4$ | $10.0$ |
    """
    degree = random.randint(1, max_degree)
    coefficients = []
    x_value1 = random.randint(-10, 5)
    x_value2 = random.randint(x_value1 + 1, 10)
    y_value1 = 0
    y_value2 = 0
    function = ""
    for i in range(degree, 0, -1):
        coefficients.append(random.randint(min_coefficient, max_coefficient))
        if coefficients[-1] > 0 and i != degree:
            function += "+"
        if i == 1:
            function += str(coefficients[-1]) + "x"
        else:
            function += str(coefficients[-1]) + "x^" + str(i)
        y_value1 += (x_value1 ** i) * coefficients[-1]
        y_value2 += (x_value2 ** i) * coefficients[-1]
    constant = random.choice(
        [c for c in range(min_coefficient, max_coefficient + 1) if c != 0]
    )
    function += ("+" if constant > 0 else "") + str(constant)
    y_value1 += constant
    y_value2 += constant
    ans = (y_value1 - y_value2) / (x_value1 - x_value2)
    problem = (
        f"Given the function ${function}$, find the average rate of change "
        f"over the interval ${x_value1}$<=x<=${x_value2}$"
    )
    solution = f"${ans}$"
    return problem, solution
