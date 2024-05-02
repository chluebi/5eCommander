from src.core.base_types import Database, Resource, Price, Gain, BaseRegion, RegionCategory


class RegionCategories:
    settlement = RegionCategory("Settlement", "🏰")
    mine = RegionCategory("Mine", "⛏️")


region_categories = [
    RegionCategories.settlement,
    RegionCategories.mine,
]


class Village(BaseRegion):

    id = 0
    name = "village"
    category = RegionCategories.settlement

    def quest_effect(self) -> tuple[list[Price], list[Gain]]:
        return [], [Gain(Resource.WORKERS, 1)]


class SmallMine(BaseRegion):

    id = 1
    name = "small mine"
    category = RegionCategories.mine

    def quest_effect(self) -> tuple[list[Price], list[Gain]]:
        return [Gain(Resource.WORKERS, 1)], [Price(Resource.GOLD, 5)]


regions = [
    Village(),
    SmallMine(),
]

assert len(set([r.id for r in regions])) == len(regions)

regions = {r.id: r for r in regions}

assert all(key == r.id for key, r in regions.items())
assert len(set([r.id for r in regions.values()])) == len(regions)
