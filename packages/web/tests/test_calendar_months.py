from web.calendar_months import month_labels, padded_month_range


def test_month_labels_length_matches_horizon():
    horizon = 5
    labels = month_labels((2026, 1), horizon)
    assert len(labels) == horizon


def test_month_labels_start_and_year_rollover():
    start_year, start_month = 2026, 11
    labels = month_labels((start_year, start_month), 3)
    assert labels == ["2026-11", "2026-12", "2027-01"]


def test_padded_month_range_extends_past_both_ends():
    assert padded_month_range((2026, 1), 4, pad_months=2) == [
        "2025-11-01",
        "2026-06-01",
    ]


def test_padded_month_range_handles_year_rollover_both_ways():
    assert padded_month_range((2026, 12), 2, pad_months=1) == [
        "2026-11-01",
        "2027-02-01",
    ]


def test_padded_month_range_without_padding():
    assert padded_month_range((2026, 1), 2, pad_months=0) == [
        "2026-01-01",
        "2026-02-01",
    ]


def test_padded_month_range_collapses_an_empty_horizon():
    assert padded_month_range((2026, 1), 0, pad_months=1) == [
        "2025-12-01",
        "2026-01-01",
    ]
