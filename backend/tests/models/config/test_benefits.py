"""Testing for models/config/benefits.py"""

# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false

import pytest
from pydantic import ValidationError

from app.models.config import User


def test_social_security_user_same_strategy(sample_config_data):
    """If the user enables the `same` strategy for social_security_pension,
    a ValidationError should be captured."""
    sample_config_data["social_security_pension"]["strategy"]["same"] = {
        "enabled": True
    }
    with pytest.raises(ValidationError, match="1 validation error"):
        User(**sample_config_data)
