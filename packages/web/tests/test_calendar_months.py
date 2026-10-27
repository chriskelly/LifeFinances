from web.calendar_months import month_labels


def test_month_labels_length_matches_horizon():
    horizon = 5
    labels = month_labels((2026, 1), horizon)
    assert len(labels) == horizon


def test_month_labels_start_and_year_rollover():
    start_year, start_month = 2026, 11
    labels = month_labels((start_year, start_month), 3)
    assert labels == ["2026-11", "2026-12", "2027-01"]
