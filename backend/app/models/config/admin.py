"""Admin and pension configuration classes"""

from pydantic import BaseModel

from app.models.config.benefits import SocialSecurityOptions
from app.models.config.strategy import StrategyConfig


class PensionOptions(SocialSecurityOptions):
    """
    Attributes
        early (Strategy): Defaults to None

        mid (Strategy): Defaults to None

        late (Strategy): Defaults to None

        net_worth (NetWorthStrategy): Defaults to None

        same (Strategy): Defaults to None

        cash_out (Strategy): Defaults to None
    """

    cash_out: StrategyConfig | None = None


class Pension(BaseModel):
    """
    Attributes
        trust_factor (float): Defaults to 1

        account_balance (float): Defaults to 0

        balance_update (float): Defaults to 2022.5

        strategy (PensionOptions): Defaults to `mid` strategy
    """

    trust_factor: float = 1
    account_balance: float = 0
    balance_update: float = 2022.5
    strategy: PensionOptions = PensionOptions(mid=StrategyConfig(chosen=True))


class Admin(BaseModel):
    """
    Attributes
        pension (Pension)
    """

    pension: Pension
