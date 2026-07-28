from exports.gsheet.model import fmt_num, is_blank, rir_band, rpe_band


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


def test_rpe_band_logged_value_is_band_top():
    assert rpe_band(7.0) == "RPE 6-7"
    assert rpe_band(8.5) == "RPE 8-9"
    assert rpe_band(6.5) == "RPE 6-7"
    assert rpe_band(10.0) == "RPE 9-10"
    assert rpe_band(9.5) == "RPE 9-10"


def test_rpe_band_low_values_collapse_to_sub5():
    assert rpe_band(5.0) == "RPE <5"
    assert rpe_band(4.5) == "RPE <5"
    assert rpe_band(3.0) == "RPE <5"


def test_rir_band_converted_value_is_band_bottom():
    assert rir_band(7.0) == "RIR 3-4"
    assert rir_band(8.5) == "RIR 1-2"
    assert rir_band(9.0) == "RIR 1-2"
    assert rir_band(10.0) == "RIR 0-1"


def test_rir_band_easy_sets_collapse_to_4plus():
    assert rir_band(6.0) == "RIR 4+"
    assert rir_band(5.5) == "RIR 4+"
    assert rir_band(4.0) == "RIR 4+"
