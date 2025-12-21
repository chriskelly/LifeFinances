"""Social Security and benefits configuration classes"""

from pydantic import BaseModel, Field

from app.models.config.strategy import StrategyConfig, StrategyOptions


class NetWorthStrategyConfig(StrategyConfig):
    """
    Attributes
        net_worth_target (float): Defaults to None
    """

    net_worth_target: float | None = Field(
        default=None,
        json_schema_extra={
            "ui": {
                "label": "Net Worth Target",
                "tooltip": "Net worth threshold for Social Security/Pension claiming strategy",
                "section": "Social Security",
                "min_value": 0,
            }
        },
    )


class SocialSecurityOptions(StrategyOptions):
    """
    Attributes
        early (Strategy): Defaults to None

        mid (Strategy): Defaults to None

        late (Strategy): Defaults to None

        net_worth (NetWorthStrategy): Defaults to None

        same (Strategy): Defaults to None
    """

    early: StrategyConfig | None = None
    mid: StrategyConfig | None = None
    late: StrategyConfig | None = None
    net_worth: NetWorthStrategyConfig | None = None
    same: StrategyConfig | None = None


class SocialSecurity(BaseModel):
    """
    Attributes
        trust_factor (float): Defaults to 1

        pension_eligible (bool): Defaults to False

        strategy (SocialSecurityOptions): Defaults to `mid` strategy

        earnings_records (dict): Defaults to empty dict
    """

    trust_factor: float = Field(
        default=1,
        json_schema_extra={
            "ui": {
                "label": "Trust Factor",
                "tooltip": "Factor to adjust Social Security benefits (1.0 = full benefits, 0.7 = 70% of benefits)",
                "section": "Social Security",
                "min_value": 0,
                "max_value": 1,
            }
        },
    )
    pension_eligible: bool = Field(
        default=False,
        json_schema_extra={
            "ui": {
                "label": "Pension Eligible",
                "tooltip": "Whether eligible for pension benefits",
                "section": "Social Security",
            }
        },
    )
    strategy: SocialSecurityOptions = Field(
        default_factory=lambda: SocialSecurityOptions(mid=StrategyConfig(chosen=True)),
        json_schema_extra={
            "ui": {
                "label": "Claiming Strategy",
                "tooltip": "Social Security claiming strategy (early, mid, late, net_worth_based)",
                "section": "Social Security",
            }
        },
    )
    earnings_records: dict = Field(
        default_factory=dict,
        json_schema_extra={
            "ui": {
                "label": "Earnings Records",
                "tooltip": "Historical earnings records for benefit calculation (year: amount)",
                "section": "Social Security",
                "widget_type": "dict",
            }
        },
    )
