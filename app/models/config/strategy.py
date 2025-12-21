"""Strategy base classes for config module"""

from collections.abc import Mapping
from typing import cast

from pydantic import BaseModel, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo


class StrategyConfig(BaseModel):
    """
    Attributes
        enabled (bool): Defaults to False

        chosen (bool): Defaults to False
    """

    enabled: bool = False
    chosen: bool = False

    @field_validator("chosen")
    @classmethod
    def chosen_forces_enabled(cls, chosen, info: ValidationInfo):
        """Forces enabled to true if chosen is true

        Note: In strategy class, enabled has to be defined before chosen in order to access it.
        """
        if chosen:
            info.data["enabled"] = True
        return chosen


class StrategyOptions(BaseModel):
    """
    Attributes:
        enabled_strategies (Mapping[str, Strategy]): Defaults to None

        chosen_strategy (tuple[str, Strategy]): Set by validator, guaranteed to be non-None
    """

    enabled_strategies: Mapping[str, StrategyConfig] | None = None
    chosen_strategy: tuple[str, StrategyConfig] = None  # type: ignore[assignment]

    @model_validator(mode="after")
    def find_enabled_and_chosen_strategies(self):
        """Find enabled and chosen strategies"""
        # Restrict only one strategy to be chosen
        chosen_cnt = sum(
            1 for _, strategy in vars(self).items() if strategy and strategy.chosen
        )
        if chosen_cnt != 1:
            raise ValueError(
                f"Exactly one {type(self).__name__} strategy must have 'chosen' set to True."
            )
        # Find enabled strategies
        self.enabled_strategies = {
            prop: strategy
            for (prop, strategy) in vars(self).items()
            if strategy and strategy.enabled
        }
        # Find chosen strategy
        chosen_strategy = next(
            (
                (prop, strategy)
                for (prop, strategy) in self.enabled_strategies.items()
                if strategy and strategy.chosen
            ),
            None,
        )
        if chosen_strategy is None:
            raise ValueError(
                f"chosen_strategy is None after validation. This should not happen if exactly one "
                f"{type(self).__name__} strategy has 'chosen' set to True."
            )
        # Type assertion: chosen_strategy is guaranteed to be non-None after the check above
        self.chosen_strategy = cast(tuple[str, StrategyConfig], chosen_strategy)
        return self
