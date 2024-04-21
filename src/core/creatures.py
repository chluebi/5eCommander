from src.core.base_types import Database, Creature, Resource, Price, Gain, Region, RegionCategory
from src.core.regions import RegionCategories


class Commoner(Creature):

    name = "commoner"
    quest_regions: list[Region] = [RegionCategories.settlement, RegionCategories.mine]

    def rally_ability_effect(self) -> tuple[list[Price], list[Gain]]:
        return [], [Gain(Resource.RALLY, 1)]
