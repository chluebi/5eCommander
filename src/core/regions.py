from src.core.base_types import Database, Resource, Price, Gain, Region, RegionCategory


class RegionCategories:
    settlement = RegionCategory("Settlement", "🏰")
    mine = RegionCategory("Mine", "⛏️")


region_categories = [
    RegionCategories.settlement,
    RegionCategories.mine,
]


class Village(Region):

    name = "village"
    category = RegionCategories.settlement

    def quest_effect(self) -> tuple[list[Price], list[Gain]]:
        return [], [Gain(Resource.WORKERS, 1)]


class SmallMine(Region):

    name = "small mine"
    category = RegionCategories.mine

    def quest_effect(self) -> tuple[list[Price], list[Gain]]:
        return [Gain(Resource.WORKERS, 1)], [Price(Resource.GOLD, 5)]


regions = [
    Village(),
    SmallMine(),
]
