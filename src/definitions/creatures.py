from __future__ import annotations
from typing import Optional, Any, List

from src.core.base_types import (
    Resource,
    Price,
    Gain,
    RegionCategory,
    RegionCategories,
    resource_changes_to_string,
    resource_changes_to_short_string,
)
from src.database.database import Database
from src.core.exceptions import CreatureCannotCampaign, CreatureCannotQuest
from src.definitions.extra_data import EXTRA_DATA


class SimpleCreature(Database.BaseCreature):
    id = -1
    name = "simple creature"
    quest_region_categories = []
    claim_cost: int = 0

    def quest_price(self) -> Optional[list[Price]]:
        return []

    def quest_gain(self) -> list[Gain]:
        return []

    def campaign_price(self) -> Optional[list[Price]]:
        return []

    def campaign_gain(self) -> list[Gain]:
        return []

    # questing
    def quest_ability_effect_short_text(self) -> str:
        price = self.quest_price()
        if price is None:
            return "❌"
        return resource_changes_to_short_string(price + self.quest_gain())

    def quest_ability_effect_full_text(self) -> str:
        price = self.quest_price()
        if price is None:
            return "Cannot be sent to locations."
        return resource_changes_to_string(price + self.quest_gain())

    def quest_ability_effect_price(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        price = self.quest_price()

        if price is None:
            raise CreatureCannotQuest()

        if price == []:
            return

        with region_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner
            owner.pay_price(price, con=con)

    def quest_ability_effect(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        gain = self.quest_gain()

        if gain == []:
            return

        with region_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner
            owner.gain(gain, con=con)

    # campaigning
    def campaign_ability_effect_short_text(self) -> str:
        price = self.campaign_price()
        if price is None:
            return "❌"
        return resource_changes_to_short_string(price + self.campaign_gain())

    def campaign_ability_effect_full_text(self) -> str:
        price = self.campaign_price()
        if price is None:
            return "Creature cannot campaign."
        return resource_changes_to_string(price + self.campaign_gain())

    def campaign_ability_effect_price(
        self,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        price = self.campaign_price()

        if price is None:
            raise CreatureCannotCampaign()

        if price == []:
            return

        with creature_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner
            owner.pay_price(price, con=con)

    def campaign_ability_effect(
        self,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
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
            owner.gain(gain, con=con)

        return strength


class Commoner(SimpleCreature):
    id = 0
    name = "commoner"
    quest_region_categories: list[RegionCategory] = [RegionCategories.market]
    claim_cost: int = 1

    def campaign_price(self) -> Optional[list[Price]]:
        return None


class Ruffian(SimpleCreature):
    id = 1
    name = "ruffian"
    quest_region_categories: list[RegionCategory] = [RegionCategories.market]
    claim_cost: int = 2

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 2)]

    def campaign_gain(self) -> list[Gain]:
        return [Gain(Resource.STRENGTH, 2)]


class Knight(SimpleCreature):
    id = 2
    name = "knight"
    quest_region_categories: list[RegionCategory] = [
        RegionCategories.noble,
        RegionCategories.market,
    ]
    claim_cost: int = 3

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 3)]

    def campaign_gain(self) -> list[Gain]:
        return [Gain(Resource.STRENGTH, 4)]


class Aristocrat(SimpleCreature):
    id = 3
    name = "aristocrat"
    quest_region_categories: list[RegionCategory] = [RegionCategories.noble]
    claim_cost: int = 3

    def campaign_gain(self) -> list[Gain]:
        return [Gain(Resource.RALLY, 3)]


class Servant(SimpleCreature):
    id = 4
    name = "servant"
    quest_region_categories: list[RegionCategory] = [RegionCategories.noble]
    claim_cost: int = 1

    def campaign_price(self) -> Optional[list[Price]]:
        return None


class Beggar(SimpleCreature):
    id = 5
    name = "beggar"
    quest_region_categories: list[RegionCategory] = [RegionCategories.market]
    claim_cost: int = 1

    def campaign_price(self) -> Optional[list[Price]]:
        return None


class Messenger(SimpleCreature):
    id = 6
    name = "messenger"
    quest_region_categories: list[RegionCategory] = [
        RegionCategories.noble,
        RegionCategories.market,
        RegionCategories.arcane,
    ]
    claim_cost: int = 2

    def campaign_price(self) -> Optional[list[Price]]:
        return None


class NoviceAdventurer(SimpleCreature):
    id = 7
    name = "novice adventurer"
    quest_region_categories: list[RegionCategory] = [
        RegionCategories.market,
        RegionCategories.dungeon,
    ]
    claim_cost: int = 2

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.STRENGTH, 1)]


class Towncrier(SimpleCreature):
    id = 8
    name = "towncrier"
    quest_region_categories: list[RegionCategory] = [RegionCategories.market]
    claim_cost: int = 2

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.RALLY, 1)]

    def campaign_price(self) -> Optional[list[Price]]:
        return None


class Spy(SimpleCreature):
    id = 9
    name = "spy"
    quest_region_categories: list[RegionCategory] = [
        RegionCategories.noble,
        RegionCategories.market,
        RegionCategories.dungeon,
    ]
    claim_cost: int = 4

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.INTEL, 1)]

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.INTEL, 2)]


class General(SimpleCreature):
    id = 10
    name = "general"
    quest_region_categories: list[RegionCategory] = [RegionCategories.noble]
    claim_cost: int = 5

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.RALLY, 3), Gain(Resource.STRENGTH, 3)]


class Scout(SimpleCreature):
    id = 11
    name = "scout"
    quest_region_categories: list[RegionCategory] = [
        RegionCategories.dungeon,
        RegionCategories.wild,
    ]
    claim_cost: int = 2

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.STRENGTH, 1)]


class NoviceMage(SimpleCreature):
    id = 12
    name = "novice mage"
    quest_region_categories: list[RegionCategory] = [RegionCategories.arcane]
    claim_cost: int = 2


class Mentor(SimpleCreature):
    id = 13
    name = "mentor"
    quest_region_categories: list[RegionCategory] = [RegionCategories.arcane]
    claim_cost: int = 3

    def quest_ability_effect_short_text(self) -> str:
        return "+1 🃏"

    def quest_ability_effect_full_text(self) -> str:
        return "Draw 1 Card."

    def quest_ability_effect(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        with region_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner
            owner.draw_cards(N=1, con=con)


class Druid(SimpleCreature):
    id = 14
    name = "druid"
    quest_region_categories: list[RegionCategory] = [RegionCategories.arcane, RegionCategories.wild]
    claim_cost: int = 3


creatures_list = [
    Commoner(),
    Ruffian(),
    Knight(),
    Aristocrat(),
    Servant(),
    Beggar(),
    Messenger(),
    NoviceAdventurer(),
    Towncrier(),
    Spy(),
    General(),
    Scout(),
    NoviceMage(),
    Mentor(),
    Druid(),
]


assert len(set([c.id for c in creatures_list])) == len(creatures_list)

creatures = {c.id: c for c in creatures_list}

assert all(key == c.id for key, c in creatures.items())
assert len(set([c.id for c in creatures.values()])) == len(creatures)
