from typing import Optional, Any, List, cast

from src.core.base_types import (
    Resource,
    Price,
    Gain,
    RegionCategory,
    resource_changes_to_string,
    resource_changes_to_short_string,
    resource_to_emoji,
    Selected,
)
from src.database.database import Database
from src.core.base_types import RegionCategories
from src.core.exceptions import NotEnoughResourcesException
from src.definitions.extra_data import (
    ExtraDataCategory,
    Choice,
    SelectedCreature,
    get_cards_in_hand_options,
    select_option_by_value,
    EXTRA_DATA,
    MissingExtraData,
    BadExtraData,
)


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
        extra_data: EXTRA_DATA = [],
    ) -> None:
        price = self.quest_price()

        if price == []:
            return

        with region_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner
            owner.pay_price(price, con=con)

    def quest_effect(
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


class RoyalGift(SimpleRegion):
    id = 0
    name = "royal gift"
    category = RegionCategories.noble

    def quest_price(self) -> list[Price]:
        return [Price(Resource.ARTEFACTS, 4)]

    def quest_gain(self) -> list[Gain]:
        return [Gain(Resource.GOLD, 5), Gain(Resource.RALLY, 5)]


class CourtPolitics(SimpleRegion):
    id = 1
    name = "court politics"
    category = RegionCategories.noble

    def quest_gain(self) -> list[Gain]:
        return [Gain(Resource.INTEL, 1)]


class Delegation(Database.BaseRegion):
    id = 2
    name = "delegation"
    category = RegionCategories.noble

    def quest_price(self) -> list[Price]:
        return [Price(Resource.GOLD, 4)]

    def quest_gain(self) -> list[Gain]:
        return [Gain(Resource.ORDERS, 1), Gain(Resource.INTEL, 1)]

    def quest_effect_short_text(self) -> str:
        return resource_changes_to_short_string(
            self.quest_price() + self.quest_gain()
        ) + ", +1 🃏".replace(" ", "\u00a0")

    def quest_effect_full_text(self) -> str:
        return resource_changes_to_string(self.quest_price() + self.quest_gain()) + " Draw 1 Card."

    def quest_effect_price(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        price = self.quest_price()

        with region_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner
            owner.pay_price(price, con=con)

    def quest_effect(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        with region_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner
            owner.gain(self.quest_gain(), con=con)
            owner.draw_cards(N=1, con=con)


class ArtefactFence(SimpleRegion):
    id = 3
    name = "artefact fence"
    category = RegionCategories.market

    def quest_price(self) -> list[Price]:
        return [Price(Resource.ARTEFACTS, 3)]

    def quest_gain(self) -> list[Gain]:
        return [Gain(Resource.GOLD, 8)]


class Collections(SimpleRegion):
    id = 4
    name = "collections"
    category = RegionCategories.market

    def quest_gain(self) -> list[Gain]:
        return [Gain(Resource.GOLD, 3)]


class Laborers(Database.BaseRegion):
    id = 5
    name = "laborers"
    category = RegionCategories.market

    def quest_price(self) -> list[Price]:
        return []

    def quest_gain(self) -> list[Gain]:
        return [Gain(Resource.GOLD, 5)]

    def quest_effect_short_text(self) -> str:
        return f"-2 🃏 → {resource_changes_to_short_string(self.quest_price() + self.quest_gain())}"

    def quest_effect_full_text(self) -> str:
        return f"Choose 2 cards in your hand. Discard them. Then gain 5 {resource_to_emoji(Resource.GOLD)}gold."

    def quest_effect(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        with region_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner

            creatures_to_discard: List[SelectedCreature] = []

            for i in range(2):
                if not extra_data:
                    raise MissingExtraData(
                        Choice(
                            0,
                            f"Choose a card from your hand to discard [{i+1}/2].",
                            get_cards_in_hand_options,
                            select_option_by_value,
                        )
                    )

                creatures_to_discard.append(cast(SelectedCreature, extra_data.pop(0)))

            for c in creatures_to_discard:
                creature_db = c.item
                owner.discard_creature_from_hand(creature_db, con=con)

            owner.gain(self.quest_gain(), con=con)


class Cave(SimpleRegion):
    id = 6
    name = "cave"
    category = RegionCategories.dungeon

    def quest_gain(self) -> list[Gain]:
        return [Gain(Resource.ARTEFACTS, 1)]


class Dungeon(SimpleRegion):
    id = 7
    name = "dungeon"
    category = RegionCategories.dungeon

    def quest_price(self) -> List[Price]:
        return [Price(Resource.INTEL, 1)]

    def quest_gain(self) -> list[Gain]:
        return [Gain(Resource.ARTEFACTS, 2)]


class HiddenLair(SimpleRegion):
    id = 8
    name = "hidden lair"
    category = RegionCategories.dungeon

    def quest_price(self) -> List[Price]:
        return [Price(Resource.INTEL, 2)]

    def quest_gain(self) -> list[Gain]:
        return [Gain(Resource.ARTEFACTS, 3)]


class Ritual(SimpleRegion):
    id = 9
    name = "ritual"
    category = RegionCategories.arcane

    def quest_price(self) -> List[Price]:
        return [Price(Resource.ARTEFACTS, 1)]

    def quest_gain(self) -> list[Gain]:
        return [Gain(Resource.MAGIC, 4)]


class Library(Database.BaseRegion):
    id = 10
    name = "library"
    category = RegionCategories.arcane

    def quest_effect_short_text(self) -> str:
        return "+2 🃏"

    def quest_effect_full_text(self) -> str:
        return "Draw 2 cards."

    def quest_effect(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        with region_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner
            owner.draw_cards(N=2, con=con)


class BindingSpell(SimpleRegion):
    id = 11
    name = "binding spell"
    category = RegionCategories.arcane

    def quest_price(self) -> List[Price]:
        return [Price(Resource.MAGIC, 10)]

    def quest_gain(self) -> list[Gain]:
        return [Gain(Resource.RALLY, 4)]


class HiddenCache(SimpleRegion):
    id = 12
    name = "hidden cache"
    category = RegionCategories.wild

    def quest_gain(self) -> list[Gain]:
        return [Gain(Resource.ARTEFACTS, 1)]


class Hunt(Database.BaseRegion):
    id = 13
    name = "hunt"
    category = RegionCategories.wild

    def quest_gain(self) -> list[Gain]:
        return [Gain(Resource.GOLD, 4)]

    def quest_effect_short_text(self) -> str:
        return (
            ">= 5 "
            + resource_to_emoji(Resource.STRENGTH)
            + " → "
            + resource_changes_to_short_string(list(self.quest_gain()))
        )

    def quest_effect_full_text(self) -> str:
        return (
            "Have 5 or more "
            + resource_to_emoji(Resource.STRENGTH)
            + "strength. "
            + resource_changes_to_string(list(self.quest_gain()))
        )

    def quest_effect_price(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        with region_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner

            player_strength = 0
            for c, s in owner.get_campaign(con=con):
                player_strength += s

            if player_strength < 5:
                raise NotEnoughResourcesException("Not enough strength. Needs 5 or more.")

    def quest_effect(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        with region_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner
            owner.gain(self.quest_gain(), con=con)


class Abandon(Database.BaseRegion):
    id = 14
    name = "abandon"
    category = RegionCategories.wild

    def quest_effect_short_text(self) -> str:
        return "🗑️"

    def quest_effect_full_text(self) -> str:
        return "Choose a card from your hand. Destroy it."

    def quest_effect(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        with region_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner

            if not extra_data:
                raise MissingExtraData(
                    Choice(
                        0,
                        "Choose a card from your hand to destroy it.",
                        get_cards_in_hand_options,
                        select_option_by_value,
                    )
                )

            selected_creature = cast(SelectedCreature, extra_data.pop(0))
            creature_db = selected_creature.item
            owner.delete_creature_in_hand(creature_db, con=con)


regions_list = [
    RoyalGift(),
    CourtPolitics(),
    Delegation(),
    ArtefactFence(),
    Collections(),
    Laborers(),
    Cave(),
    Dungeon(),
    HiddenLair(),
    Ritual(),
    Library(),
    BindingSpell(),
    HiddenCache(),
    Hunt(),
    Abandon(),
]


assert len(set([r.id for r in regions_list])) == len(regions_list)

regions = {r.id: r for r in regions_list}

assert all(key == r.id for key, r in regions.items())
assert len(set([r.id for r in regions.values()])) == len(regions)
