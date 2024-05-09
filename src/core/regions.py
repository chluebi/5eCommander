from src.core.base_types import (
    Database,
    Resource,
    Price,
    Gain,
    BaseRegion,
    RegionCategory,
    resource_changes_to_string,
    resource_changes_to_short_string,
)


class RegionCategories:
    settlement = RegionCategory("Settlement", "🏰")
    mine = RegionCategory("Mine", "⛏️")


region_categories = [
    RegionCategories.settlement,
    RegionCategories.mine,
]


class SimpleRegion(BaseRegion):

    id = -1
    name = "simple region"
    category = None

    def quest_price(self) -> list[Price]:
        return []

    def quest_gain(self) -> list[Gain]:
        return []

    def quest_effect_short_text(self) -> str:
        return resource_changes_to_short_string(self.quest_price() + self.quest_gain())

    def quest_effect_full_text(self) -> str:
        return resource_changes_to_string(self.quest_price() + self.quest_gain())

    def quest_effect_price(self, region_db, creature_db, con=None, extra_data={}):
        price = self.quest_price()

        if price == []:
            return

        with region_db.parent.transaction(con=con) as con:
            owner: Database.Player = creature_db.owner
            owner.pay_price(price, con=con, extra_data=extra_data)

    def quest_effect(self, region_db, creature_db, con=None, extra_data={}):
        gain = self.quest_gain()

        if gain == []:
            return

        with region_db.parent.transaction(con=con) as con:
            owner: Database.Player = creature_db.owner
            owner.gain(gain, con=con, extra_data=extra_data)


class Village(SimpleRegion):

    id = 0
    name = "village"
    category = RegionCategories.settlement

    def quest_gain(self) -> list[Gain]:
        return [Gain(Resource.WORKERS, 1)]


class SmallMine(SimpleRegion):

    id = 1
    name = "small mine"
    category = RegionCategories.mine

    def quest_price(self) -> list[Price]:
        return [Price(Resource.WORKERS, 1)]

    def quest_gain(self) -> list[Gain]:
        return [Gain(Resource.GOLD, 5)]


regions = [
    Village(),
    SmallMine(),
]

assert len(set([r.id for r in regions])) == len(regions)

regions = {r.id: r for r in regions}

assert all(key == r.id for key, r in regions.items())
assert len(set([r.id for r in regions.values()])) == len(regions)
