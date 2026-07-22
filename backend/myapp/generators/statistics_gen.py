"""Solveki-local statistics / data-analysis generators.

These cover the computable gaps in Georgia's "Statistical Reasoning" course
and the data-analysis strands of Algebra. Every generator here is named with a
``stat_`` prefix, takes no required arguments, and returns a ``(problem,
solution)`` pair of LaTeX strings. Problem statements are written to be
regex-parseable (datasets are rendered as e.g. ``data set: 3, 7, 1, 9, 4``) so
the math-correctness tests can recover the inputs and recompute the answer.
"""
import math
import random
from math import gcd

from ._registry import register
from ._format import num as _fmt  # noqa: F401 — typeable number formatter


def _median(values):
    """Median of a list, using the mean of the two middle values when even."""
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


@register
def stat_five_number_summary(min_val=1, max_val=20):
    r"""Five-Number Summary

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Given the data set: 3, 7, 1, 9, 4. Find the five-number summary. | $1, 3, 4, 7, 9$ |

    Q1 and Q3 are defined as the medians of the lower and upper halves, with
    the overall median excluded from both halves when the count is odd.
    """
    n = random.choice([5, 6, 7, 8])
    data = [random.randint(min_val, max_val) for _ in range(n)]
    ordered = sorted(data)

    mid = n // 2
    if n % 2 == 1:
        lower = ordered[:mid]
        upper = ordered[mid + 1:]
    else:
        lower = ordered[:mid]
        upper = ordered[mid:]

    minimum = ordered[0]
    maximum = ordered[-1]
    q1 = _median(lower)
    med = _median(ordered)
    q3 = _median(upper)

    problem = (
        f"Given the data set: {', '.join(str(v) for v in data)}. "
        "Find the five-number summary (minimum, Q1, median, Q3, maximum). "
        "Q1 and Q3 are the medians of the lower and upper halves, excluding "
        "the overall median when the number of values is odd. "
        "Give your answer as min, Q1, median, Q3, max."
    )
    solution = (
        f"${_fmt(minimum)}, {_fmt(q1)}, {_fmt(med)}, {_fmt(q3)}, {_fmt(maximum)}$"
    )
    return problem, solution


@register
def stat_z_score(min_val=0, max_val=100):
    r"""Z-Score

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | A value of x = 15 comes from a distribution with mean = 10 and standard deviation = 2.5. Find its z-score. | $2$ |

    z = (x - mean) / standard deviation, rounded to 3 decimal places.
    """
    mean = random.randint(min_val, max_val)
    sd = random.choice([1, 2, 2.5, 4, 5, 8, 10])
    x = random.randint(min_val, max_val)

    z = (x - mean) / sd
    problem = (
        f"A value of x = {_fmt(x)} comes from a distribution with mean = "
        f"{_fmt(mean)} and standard deviation = {_fmt(sd)}. Find its z-score "
        "(rounded to 3 decimal places)."
    )
    solution = f"${_fmt(z)}$"
    return problem, solution


def _integer_points(max_val=12):
    """Return 4-5 integer (x, y) points with non-zero x- and y-variance."""
    while True:
        count = random.choice([4, 5])
        xs = random.sample(range(0, max_val), count)  # distinct x -> Sxx > 0
        ys = [random.randint(0, max_val) for _ in range(count)]
        if len(set(ys)) > 1:  # non-constant y -> Syy > 0
            return list(zip(xs, ys))


def _points_str(points):
    return ", ".join(f"({x}, {y})" for x, y in points)


@register
def stat_correlation_coefficient(max_val=12):
    r"""Pearson Correlation Coefficient

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Given the points: (1, 2), (3, 5), (4, 4), (6, 7). Find the correlation coefficient r. | $0.898$ |

    Pearson r = Sxy / sqrt(Sxx * Syy), rounded to 3 decimal places.
    """
    points = _integer_points(max_val)
    n = len(points)
    mean_x = sum(x for x, _ in points) / n
    mean_y = sum(y for _, y in points) / n
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in points)
    sxx = sum((x - mean_x) ** 2 for x, _ in points)
    syy = sum((y - mean_y) ** 2 for _, y in points)

    r = sxy / math.sqrt(sxx * syy)
    problem = (
        f"Given the points: {_points_str(points)}. Find the Pearson "
        "correlation coefficient r (rounded to 3 decimal places)."
    )
    solution = f"${_fmt(r)}$"
    return problem, solution


@register
def stat_regression_line(max_val=12):
    r"""Least-Squares Regression Line

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | Given the points: (1, 2), (3, 5), (4, 4), (6, 7). Find the least-squares regression line. | $y = 0.836 x + 1.291$ |

    Slope m = Sxy / Sxx, intercept b = mean_y - m * mean_x, both rounded to 3dp.
    """
    points = _integer_points(max_val)
    n = len(points)
    mean_x = sum(x for x, _ in points) / n
    mean_y = sum(y for _, y in points) / n
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in points)
    sxx = sum((x - mean_x) ** 2 for x, _ in points)

    m = sxy / sxx
    b = mean_y - m * mean_x

    b_val = round(b, 3)
    sign = "+" if b_val >= 0 else "-"
    problem = (
        f"Given the points: {_points_str(points)}. Find the least-squares "
        "regression line y = m x + b (m and b rounded to 3 decimal places)."
    )
    solution = f"$y = {_fmt(m)} x {sign} {_fmt(abs(b_val))}$"
    return problem, solution


@register
def stat_margin_of_error(min_n=30, max_n=1500):
    r"""Margin of Error for a Proportion

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | A poll has sample proportion p = 0.4, sample size n = 100, and critical value z = 1.96. Find the margin of error. | $0.096$ |

    Margin of error = z * sqrt(p(1 - p) / n), rounded to 3 decimal places.
    """
    p = random.choice([0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9])
    z = random.choice([1.645, 1.96, 2.576])
    n = random.randint(min_n, max_n)

    moe = z * math.sqrt(p * (1 - p) / n)
    problem = (
        f"A poll has sample proportion p = {_fmt(p)}, sample size n = {n}, and "
        f"critical value z = {_fmt(z)}. Find the margin of error "
        "z * sqrt(p(1 - p) / n) (rounded to 3 decimal places)."
    )
    solution = f"${_fmt(moe)}$"
    return problem, solution


@register
def stat_standard_error_mean(max_sd=50, max_n=400):
    r"""Standard Error of the Mean

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | A sample has standard deviation s = 12 and size n = 36. Find the standard error of the mean. | $2$ |

    Standard error = s / sqrt(n), rounded to 3 decimal places.
    """
    sd = random.randint(1, max_sd)
    n = random.randint(2, max_n)

    se = sd / math.sqrt(n)
    problem = (
        f"A sample has standard deviation s = {sd} and size n = {n}. Find the "
        "standard error of the mean s / sqrt(n) (rounded to 3 decimal places)."
    )
    solution = f"${_fmt(se)}$"
    return problem, solution


@register
def stat_sample_proportion_ci(min_n=30, max_n=1500):
    r"""Confidence Interval for a Proportion

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | A sample has proportion p = 0.4, size n = 100, and critical value z = 1.96. Find the confidence interval p +/- z*sqrt(p(1-p)/n). | $(0.304, 0.496)$ |

    Interval endpoints p +/- z * sqrt(p(1 - p) / n), each rounded to 3dp.
    """
    p = random.choice([0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9])
    z = random.choice([1.645, 1.96, 2.576])
    n = random.randint(min_n, max_n)

    moe = z * math.sqrt(p * (1 - p) / n)
    low = p - moe
    high = p + moe
    problem = (
        f"A sample has proportion p = {_fmt(p)}, size n = {n}, and critical "
        f"value z = {_fmt(z)}. Find the confidence interval "
        "p +/- z*sqrt(p(1-p)/n) (endpoints rounded to 3 decimal places). "
        "Give your answer as (low, high)."
    )
    solution = f"$({_fmt(low)}, {_fmt(high)})$"
    return problem, solution


@register
def stat_relative_frequency(max_count=20):
    r"""Relative Frequency

    | Ex. Problem | Ex. Solution |
    | --- | --- |
    | A survey recorded these category counts: 4, 7, 9, 5. Find the relative frequency of category 2. | $7/25$ |

    Relative frequency = category count / total count, as a reduced fraction.
    """
    k = random.choice([3, 4, 5])
    counts = [random.randint(1, max_count) for _ in range(k)]
    index = random.randint(0, k - 1)  # 0-based
    count = counts[index]
    total = sum(counts)

    divisor = gcd(count, total)
    numerator = count // divisor
    denominator = total // divisor

    problem = (
        f"A survey recorded these category counts: {', '.join(str(c) for c in counts)}. "
        f"Find the relative frequency of category {index + 1} "
        "(as a reduced fraction)."
    )
    solution = f"${numerator}/{denominator}$"
    return problem, solution
