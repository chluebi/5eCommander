from src.core.base_types import StartCondition, RegionCategory


class RegionCategories:
    settlement = RegionCategory("Settlement", "🏰")
    mine = RegionCategory("Mine", "⛏️")


region_categories = [
    RegionCategories.settlement,
    RegionCategories.mine,
]


class Village:

    name = "village"
    category = RegionCategories.settlement

    def __init__(self):
        pass

    def mission(self, player):
        return


class SmallMine:

    name = "small mine"
    category = RegionCategories.mine

    def __init__(self):
        pass

    def mission(self, player):
        return


regions = [
    Village(),
    SmallMine(),
]

start_condition = StartCondition([Village(), SmallMine()])
