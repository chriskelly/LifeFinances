import pytest
from core.models import (
    DEFAULT_PERCENTILES,
    AdvancedConfig,
    normalize_percentiles,
)
from pydantic import ValidationError


def test_normalize_percentiles_sorts_ascending():
    unsorted = [90, 5, 50]
    expected = sorted(unsorted)

    assert normalize_percentiles(unsorted) == expected


def test_normalize_percentiles_rejects_empty():
    with pytest.raises(ValueError, match="non-empty"):
        normalize_percentiles([])


def test_normalize_percentiles_rejects_out_of_range():
    with pytest.raises(ValueError, match="0..100"):
        normalize_percentiles([50, 101])


def test_normalize_percentiles_rejects_duplicates() -> None:
    duplicate = 50
    values = [5, duplicate, duplicate, 95]

    with pytest.raises(ValueError, match="duplicates"):
        normalize_percentiles(values)


def test_advanced_config_applies_duplicate_rejection() -> None:
    duplicate = 25

    with pytest.raises(ValidationError, match="duplicates"):
        AdvancedConfig(percentiles=[duplicate, duplicate])


def test_advanced_config_uses_normalize_percentiles():
    # Our validator must apply the same normalization (sort), not leave input order.
    unsorted = [95, 5, 50]
    config = AdvancedConfig(percentiles=unsorted)

    assert config.percentiles == normalize_percentiles(unsorted)
    assert DEFAULT_PERCENTILES == [5, 50, 95]  # pinned: tpaw UI low/mid/high
