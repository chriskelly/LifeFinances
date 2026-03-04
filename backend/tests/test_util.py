"""Testing for util.py"""

import pytest

from app.util import constrain


class TestConstrain:
    def test_lower_limit(self):
        """Returned value should be equal to lower limit"""
        assert constrain(value=5, low=10, high=20) == pytest.approx(10)

    def test_upper_limit(self):
        """Returned value should be equal to upper limit"""
        assert constrain(value=25, low=10, high=20) == pytest.approx(20)

    def test_within_limits(self):
        """Returned value should be equal to input value"""
        assert constrain(value=15, low=10, high=20) == pytest.approx(15)

    def test_equal_limits(self):
        """Returned value should be equal to either limit"""
        assert constrain(value=10, low=10, high=10) == pytest.approx(10)

    def test_float(self):
        """Constrain should work with floats"""
        assert constrain(value=5.5, low=1.2, high=3.7) == pytest.approx(3.7)
