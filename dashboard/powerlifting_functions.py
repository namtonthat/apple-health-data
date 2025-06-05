def calculate_dots(total_kg: float, bodyweight_kg: float, sex: str = "male") -> float:
    """
    Calculates DOTS score using IPF formula for the given bodyweight and sex.

    Returns:
        float: DOTS score rounded to 2 decimal places.
    """
    if sex.lower() == "male":
        a, b, c, d, e = (
            47.46178854,
            8.472061379,
            0.07369410346,
            -0.001395833811,
            7.076659730e-06,
        )
    elif sex.lower() == "female":
        a, b, c, d, e = (
            -125.4255398,
            13.71219419,
            -0.03307250631,
            0.00004840116767,
            -1.812303927e-08,
        )
    else:
        raise ValueError("Sex must be 'male' or 'female'")

    bw = bodyweight_kg
    coeff = a + b * bw + c * bw**2 + d * bw**3 + e * bw**4
    return round((500 / coeff) * total_kg, 2)


def estimate_one_rep_max(weight: float, reps: int) -> float:
    """Estimate a one-repetition max using the Epley formula."""

    try:
        w = float(weight)
        r = float(reps)
    except (TypeError, ValueError):
        return float("nan")

    return w * (1 + r / 30)
