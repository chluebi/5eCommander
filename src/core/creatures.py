from __future__ import annotations
from typing import Optional, Any, List

from src.core.base_types import (
    Resource,
    Price,
    Gain,
    BaseRegion,
    RegionCategory,
    resource_changes_to_string,
    resource_changes_to_short_string,
)
from src.database.database import Database
from src.core.regions import RegionCategories
from src.core.exceptions import CreatureCannotCampaign


class SimpleCreature(Database.BasicCreature):

    id = -1
    name = "simple creature"
    quest_region_categories = []
    claim_cost: int = 0

    def quest_price(self) -> list[Price]:
        return []

    def quest_gain(self) -> list[Gain]:
        return []

    def campaign_price(self) -> list[Price]:
        return []

    def campaign_gain(self) -> list[Gain]:
        return []

    # questing
    def quest_ability_effect_short_text(self) -> str:
        return resource_changes_to_short_string(self.quest_price() + self.quest_gain())

    def quest_ability_effect_full_text(self) -> str:
        return resource_changes_to_string(self.quest_price() + self.quest_gain())

    def quest_ability_effect_price(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: dict[Any, Any] = {},
    ) -> None:
        price = self.quest_price()

        if price == []:
            return

        with region_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner
            owner.pay_price(price, con=con, extra_data=extra_data)

    def quest_ability_effect(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: dict[Any, Any] = {},
    ) -> None:
        gain = self.quest_gain()

        if gain == []:
            return

        with region_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner
            owner.gain(gain, con=con, extra_data=extra_data)

    # campaigning
    def campaign_ability_effect_short_text(self) -> str:
        return resource_changes_to_short_string(self.campaign_price() + self.campaign_gain())

    def campaign_ability_effect_full_text(self) -> str:
        return resource_changes_to_string(self.campaign_price() + self.campaign_gain())

    def campaign_ability_effect_price(
        self,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: dict[Any, Any] = {},
    ) -> None:
        price = self.campaign_price()

        if price == []:
            return

        with creature_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner
            owner.pay_price(price, con=con, extra_data=extra_data)

    def campaign_ability_effect(
        self,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: dict[Any, Any] = {},
    ) -> int:
        gain = self.campaign_gain()

        if gain == []:
            return 0

        strength = 0
        for g in gain:
            if g.resource == Resource.STRENGTH:
                strength += g.amount

        with creature_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner
            owner.gain(gain, con=con, extra_data=extra_data)

        return strength


class Commoner(SimpleCreature):

    id = 0
    name = "commoner"
    quest_region_categories: list[RegionCategory] = [
        RegionCategories.settlement,
        RegionCategories.mine,
    ]
    claim_cost: int = 1

    def campaign_gain(self) -> list[Gain]:
        return [Gain(Resource.RALLY, 1)]


creatures_list = [Commoner()]

assert len(set([c.id for c in creatures_list])) == len(creatures_list)

creatures = {c.id: c for c in creatures_list}

assert all(key == c.id for key, c in creatures.items())
assert len(set([c.id for c in creatures.values()])) == len(creatures)
