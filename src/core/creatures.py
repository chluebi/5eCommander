from src.core.base_types import (
    Database,
    BaseCreature,
    Resource,
    Price,
    Gain,
    BaseRegion,
    RegionCategory,
)
from src.core.regions import RegionCategories


class Commoner(BaseCreature):

    id = 0
    name = "commoner"
    quest_regions: list[BaseRegion] = [RegionCategories.settlement, RegionCategories.mine]

    def rally_ability_effect(self) -> tuple[list[Price], list[Gain]]:
        return [], [Gain(Resource.RALLY, 1)]
    
creatures = [
    Commoner()
]

assert len(set([c.id for c in creatures])) == len(creatures)
