from exports.gsheet.model import fmt_num, is_blank


def test_is_blank_empty_and_whitespace():
    assert is_blank("")
    assert is_blank("   ")


def test_is_blank_rate_placeholder_any_case():
    assert is_blank("RATE")
    assert is_blank("rate")
    assert is_blank(" Rate ")


def test_is_blank_false_for_values():
    assert not is_blank("97.5")
    assert not is_blank("RPE 6-7")
    assert not is_blank("0")


def test_fmt_num_strips_trailing_zeros():
    assert fmt_num(97.5) == "97.5"
    assert fmt_num(150.0) == "150"
    assert fmt_num(102.5) == "102.5"
