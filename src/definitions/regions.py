from typing import Optional, Any, List

from src.core.base_types import (
    Resource,
    Price,
    Gain,
    RegionCategory,
    resource_changes_to_string,
    resource_changes_to_short_string,
)
from src.database.database import Database


class RegionCategories:
    settlement = RegionCategory("Settlement", "🏰")
    mine = RegionCategory("Mine", "⛏️")


region_categories = [
    RegionCategories.settlement,
    RegionCategories.mine,
]


class SimpleRegion(Database.BaseRegion):

    id = -1
    name = "simple region"
    category: Optional[RegionCategory] = None

    def quest_price(self) -> list[Price]:
        return []

    def quest_gain(self) -> list[Gain]:
        return []

    def quest_effect_short_text(self) -> str:
        return resource_changes_to_short_string(self.quest_price() + self.quest_gain())

    def quest_effect_full_text(self) -> str:
        return resource_changes_to_string(self.quest_price() + self.quest_gain())

    def quest_effect_price(
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

    def quest_effect(
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


class Village(SimpleRegion):

    id = 0
    name = "village"
    category = RegionCategories.settlement

    def quest_gain(self) -> list[Gain]:
        return [Gain(Resource.INTEL, 1)]


class SmallMine(SimpleRegion):

    id = 1
    name = "small mine"
    category = RegionCategories.mine

    def quest_price(self) -> list[Price]:
        return [Price(Resource.INTEL, 1)]

    def quest_gain(self) -> list[Gain]:
        return [Gain(Resource.GOLD, 5)]


regions_list = [
    Village(),
    SmallMine(),
]

assert len(set([r.id for r in regions_list])) == len(regions_list)

regions = {r.id: r for r in regions_list}

assert all(key == r.id for key, r in regions.items())
assert len(set([r.id for r in regions.values()])) == len(regions)
