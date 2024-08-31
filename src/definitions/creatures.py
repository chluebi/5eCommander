from __future__ import annotations
from typing import Optional, Any, List, cast

from src.core.base_types import (
    Resource,
    Price,
    Gain,
    RegionCategory,
    RegionCategories,
    resource_changes_to_string,
    resource_changes_to_short_string,
    resource_to_emoji,
    Selected,
)
from src.database.database import Database
from src.core.exceptions import CreatureCannotCampaign, CreatureCannotQuest
from src.definitions.extra_data import (
    EXTRA_DATA,
    MissingExtraData,
    Choice,
    get_cards_in_discard_options,
    get_cards_in_hand_options,
    get_cards_in_deck_options,
    get_cards_in_campaign_options,
    select_option_by_value,
    SelectedCreature,
    SelectedRegion,
)


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
            return "Cannot campaign."
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


class Servant(SimpleCreature):
    id = 1
    name = "servant"
    quest_region_categories: list[RegionCategory] = [RegionCategories.noble]
    claim_cost: int = 0

    def campaign_price(self) -> Optional[list[Price]]:
        return None


class Commoner(SimpleCreature):
    id = 2
    name = "commoner"
    quest_region_categories: list[RegionCategory] = [RegionCategories.market]
    claim_cost: int = 0

    def campaign_price(self) -> Optional[list[Price]]:
        return None


class NoviceAdventurer(SimpleCreature):
    id = 3
    name = "novice adventurer"
    quest_region_categories: list[RegionCategory] = [RegionCategories.dungeon]
    claim_cost: int = 1

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.RALLY, 1)]

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 1)]

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.STRENGTH, 1)]


class NoviceMage(SimpleCreature):
    id = 4
    name = "novice mage"
    quest_region_categories: list[RegionCategory] = [RegionCategories.arcane]
    claim_cost: int = 1

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.RALLY, 1)]

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 1)]

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.STRENGTH, 1)]


class LoyalSquire(SimpleCreature):
    id = 5
    name = "loyal squire"
    quest_region_categories: list[RegionCategory] = [
        RegionCategories.noble,
        RegionCategories.market,
        RegionCategories.dungeon,
        RegionCategories.arcane,
        RegionCategories.wild,
    ]
    claim_cost: int = 3

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.RALLY, 2)]

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 2)]

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.STRENGTH, 2)]


class Herald(SimpleCreature):
    id = 6
    name = "herald"
    quest_region_categories: list[RegionCategory] = [RegionCategories.noble]
    claim_cost: int = 1

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.RALLY, 1)]


class Local(SimpleCreature):
    id = 7
    name = "local"
    quest_region_categories: list[RegionCategory] = [RegionCategories.market]
    claim_cost: int = 1

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.RALLY, 1)]


class Guide(SimpleCreature):
    id = 8
    name = "guide"
    quest_region_categories: list[RegionCategory] = [RegionCategories.dungeon]
    claim_cost: int = 1

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.RALLY, 1)]


class MagicStudent(SimpleCreature):
    id = 9
    name = "magic student"
    quest_region_categories: list[RegionCategory] = [RegionCategories.arcane]
    claim_cost: int = 1

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.RALLY, 1)]


class Farmer(SimpleCreature):
    id = 10
    name = "farmer"
    quest_region_categories: list[RegionCategory] = [RegionCategories.wild]
    claim_cost: int = 1

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.RALLY, 1)]


class Ambassador(SimpleCreature):
    id = 11
    name = "ambassador"
    quest_region_categories: list[RegionCategory] = [RegionCategories.noble]
    claim_cost: int = 3

    def quest_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 1)]

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.INTEL, 1)]

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 1)]

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.RALLY, 3)]


class Trader(SimpleCreature):
    id = 12
    name = "trader"
    quest_region_categories: list[RegionCategory] = [RegionCategories.market]
    claim_cost: int = 3

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.GOLD, 2)]

    def campaign_price(self) -> None:
        return None


class Explorer(SimpleCreature):
    id = 13
    name = "explorer"
    quest_region_categories: list[RegionCategory] = [RegionCategories.dungeon]
    claim_cost: int = 3

    def quest_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 2)]

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.ARTEFACTS, 1)]

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 2)]

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.STRENGTH, 3)]


class Mentor(SimpleCreature):
    id = 14
    name = "mentor"
    quest_region_categories: list[RegionCategory] = [RegionCategories.arcane]
    claim_cost: int = 2

    def quest_ability_effect_short_text(self) -> str:
        return "+1 🃏"

    def quest_ability_effect_full_text(self) -> str:
        return "Draw 1 Card."

    def campaign_ability_effect_short_text(self) -> str:
        return "❌"

    def campaign_ability_effect_full_text(self) -> str:
        return "Cannot campaign."

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


class Hunter(SimpleCreature):
    id = 15
    name = "hunter"
    quest_region_categories: list[RegionCategory] = [RegionCategories.wild]
    claim_cost: int = 2

    def quest_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 2)]

    def quest_ability_effect_short_text(self) -> str:
        return f"{resource_changes_to_short_string(self.quest_price())} → 🗑️"

    def quest_ability_effect_full_text(self) -> str:
        return f"{resource_changes_to_string(self.quest_price())}. Trash target card in your hand."

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 1)]

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.STRENGTH, 1)]

    def quest_ability_effect(
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


class Messenger(SimpleCreature):
    id = 16
    name = "messenger"
    quest_region_categories: list[RegionCategory] = [
        RegionCategories.noble,
        RegionCategories.market,
    ]
    claim_cost: int = 2

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.INTEL, 1)]

    def quest_ability_effect_short_text(self) -> str:
        return f"{RegionCategories.noble.emoji}❔ → {resource_changes_to_short_string(self.quest_gain())}"

    def quest_ability_effect_full_text(self) -> str:
        return f"For each other played creature to a {RegionCategories.noble.emoji} {str(RegionCategories.noble.name).title()} region, {resource_changes_to_string(self.quest_gain())}"

    def campaign_price(self) -> None:
        return None

    def quest_ability_effect(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        with region_db.parent.transaction(parent=con) as con:
            for c, _ in creature_db.owner.get_played(con=con):
                occupies = c.occupies(con=con)
                if occupies is not None:
                    r, _ = occupies
                    if (
                        r.region.category is not None
                        and RegionCategories.noble in r.region.category
                    ):
                        creature_db.owner.gain(self.quest_gain(), con=con)


class Towncrier(SimpleCreature):
    id = 17
    name = "town crier"
    quest_region_categories: list[RegionCategory] = [RegionCategories.market]
    claim_cost: int = 3

    def quest_price(self) -> List[Price]:
        return [Price(Resource.STRENGTH, 5)]

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.RALLY, 3)]

    def quest_ability_effect_short_text(self) -> str:
        return f">= 5 {resource_to_emoji(Resource.STRENGTH)}❔ → {resource_changes_to_short_string(self.quest_gain())}"

    def quest_ability_effect_full_text(self) -> str:
        return f"If you currently have 5 or more {resource_to_emoji(Resource.STRENGTH)} {str(Resource.STRENGTH).lower().title()}, {resource_changes_to_string(self.quest_gain())}"

    def campaign_price(self) -> None:
        return None

    def quest_ability_effect(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        with region_db.parent.transaction(parent=con) as con:
            if creature_db.owner.get_resources(con=con)[Resource.STRENGTH] >= 5:
                creature_db.owner.gain(self.quest_gain(), con=con)


class Quartermaster(SimpleCreature):
    id = 18
    name = "quartermaster"
    quest_region_categories: list[RegionCategory] = [RegionCategories.market]
    claim_cost: int = 3

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.ORDERS, 1)]

    def quest_ability_effect_short_text(self) -> str:
        return f"{RegionCategories.dungeon.emoji}❔ → {resource_changes_to_short_string(self.quest_gain())}"

    def quest_ability_effect_full_text(self) -> str:
        return f"For each other played creature to a {RegionCategories.dungeon.emoji} {str(RegionCategories.dungeon.name).title()} region, {resource_changes_to_string(self.quest_gain())}"

    def campaign_price(self) -> None:
        return None

    def quest_ability_effect(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        with region_db.parent.transaction(parent=con) as con:
            for c, _ in creature_db.owner.get_played(con=con):
                occupies = c.occupies(con=con)
                if occupies is not None:
                    r, _ = occupies
                    if (
                        r.region.category is not None
                        and RegionCategories.dungeon in r.region.category
                    ):
                        creature_db.owner.gain(self.quest_gain(), con=con)


class ArcaneTutor(SimpleCreature):
    id = 19
    name = "arcane tutor"
    quest_region_categories: list[RegionCategory] = [RegionCategories.arcane]

    def quest_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 1)]

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.ORDERS, 1)]

    def quest_ability_effect_short_text(self) -> str:
        return f"{resource_changes_to_short_string(self.quest_price())} → 🔍🃏"

    def quest_ability_effect_full_text(self) -> str:
        return f"{resource_changes_to_string(self.quest_price())}. Draw target card from your deck."

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 1)]

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.MAGIC, 3)]

    def quest_ability_effect(
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
                        "Choose a card from your deck to draw it.",
                        get_cards_in_deck_options,
                        select_option_by_value,
                    )
                )

            selected_creature = cast(SelectedCreature, extra_data.pop(0))
            creature_db = selected_creature.item
            owner.draw_creature_from_deck(creature_db, con=con)


class Druid(SimpleCreature):
    id = 20
    name = "druid"
    quest_region_categories: list[RegionCategory] = [RegionCategories.arcane, RegionCategories.wild]

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.MAGIC, 1)]

    def quest_ability_effect_short_text(self) -> str:
        return f"X🃏{RegionCategories.wild.emoji} → X{resource_to_emoji(Resource.MAGIC)}"

    def quest_ability_effect_full_text(self) -> str:
        return f"{resource_changes_to_string(self.quest_gain()).capitalize()} for each wild card in your deck (not discard or played)."

    def campaign_price(self) -> None:
        return None

    def quest_ability_effect(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        with region_db.parent.transaction(parent=con) as con:
            wild_creatures = [
                c
                for c in creature_db.owner.get_deck()
                if RegionCategories.wild in c.creature.quest_region_categories
            ]
            creature_db.owner.gain([Gain(Resource.MAGIC, len(wild_creatures))], con=con)


class RetiredGeneral(SimpleCreature):
    id = 21
    name = "retired general"
    quest_region_categories: list[RegionCategory] = [RegionCategories.noble]
    claim_cost: int = 4

    def quest_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 2)]

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.RALLY, 3)]

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.STRENGTH, 5)]

    def campaign_ability_effect_short_text(self) -> str:
        return f">= 10 {resource_to_emoji(Resource.RALLY)}❔ → {resource_changes_to_short_string(self.campaign_gain())}"

    def campaign_ability_effect_full_text(self) -> str:
        return f"If you currently have 10 or more {resource_to_emoji(Resource.RALLY)} {str(Resource.RALLY).lower().title()}, {resource_changes_to_string(self.campaign_gain())}."

    def campaign_ability_effect(
        self,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: List[Selected] = [],
    ) -> int:
        with creature_db.parent.transaction(parent=con) as con:
            if creature_db.owner.get_resources(con=con)[Resource.RALLY] >= 10:
                creature_db.owner.gain(self.quest_gain(), con=con)

        return 0


class SwordSmith(SimpleCreature):
    id = 22
    name = "swordsmith"
    quest_region_categories: list[RegionCategory] = [RegionCategories.market]
    claim_cost: int = 4

    def quest_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 3)]

    def quest_ability_effect_short_text(self) -> str:
        return f"{resource_changes_to_short_string(self.quest_price())} → X🏹"

    def quest_ability_effect_full_text(self) -> str:
        return f"{resource_changes_to_string(self.quest_price())}. Each of your campaigning creatures gains +1 {resource_to_emoji(Resource.STRENGTH)} {str(Resource.STRENGTH).lower().title()}."

    def campaign_price(self) -> None:
        return None

    def quest_ability_effect(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        with region_db.parent.transaction(parent=con) as con:
            for c, s in creature_db.owner.get_campaign(con=con):
                c.change_strength(s + 1, con=con)


class Scout(SimpleCreature):
    id = 23
    name = "scout"
    quest_region_categories: list[RegionCategory] = [
        RegionCategories.dungeon,
        RegionCategories.wild,
    ]
    claim_cost: int = 3

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 2)]

    def campaign_ability_effect_short_text(self) -> str:
        return f"{resource_changes_to_short_string(self.campaign_price())} → ⤵️🃏"

    def campaign_ability_effect_full_text(self) -> str:
        return f"{resource_changes_to_string(self.campaign_gain())}. Return target creature from your campaign to your discard."

    def campaign_ability_effect(
        self,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: List[Selected] = [],
    ) -> int:
        with creature_db.parent.transaction(parent=con) as con:
            if not extra_data:
                raise MissingExtraData(
                    Choice(
                        0,
                        "Choose a card from your campaign to return it.",
                        get_cards_in_campaign_options,
                        select_option_by_value,
                    )
                )

            selected_creature = cast(SelectedCreature, extra_data.pop(0))
            creature_db.owner.remove_creature_from_deck(selected_creature.item, con=con)
            creature_db.owner.add_to_discard(selected_creature.item, con=con)

        return 0


class Librarian(SimpleCreature):
    id = 24
    name = "librarian"
    quest_region_categories: list[RegionCategory] = [RegionCategories.arcane]
    claim_cost: int = 5

    def quest_ability_effect_short_text(self) -> str:
        return "+3 🃏"

    def quest_ability_effect_full_text(self) -> str:
        return "Draw 3 Cards."

    def campaign_ability_effect_short_text(self) -> str:
        return "❌"

    def campaign_ability_effect_full_text(self) -> str:
        return "Cannot campaign."

    def quest_ability_effect(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        with region_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner
            owner.draw_cards(N=3, con=con)


class Nymph(SimpleCreature):
    id = 25
    name = "librarian"
    quest_region_categories: list[RegionCategory] = [RegionCategories.wild]
    claim_cost: int = 4

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.INTEL, 1)]

    def campaign_price(self) -> None:
        return None


class Soldier(SimpleCreature):
    id = 26
    name = "soldier"
    quest_region_categories: list[RegionCategory] = [RegionCategories.noble]
    claim_cost: int = 2

    def quest_gain(self) -> List[Gain]:
        return []

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 1)]

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.STRENGTH, 2)]


class Bandit(SimpleCreature):
    id = 28
    name = "bandit"
    quest_region_categories: list[RegionCategory] = [RegionCategories.market]
    claim_cost: int = 2

    def quest_gain(self) -> List[Gain]:
        return []

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 2)]

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.STRENGTH, 3)]


class Paladin(SimpleCreature):
    id = 29
    name = "paladin"
    quest_region_categories: list[RegionCategory] = [
        RegionCategories.noble,
        RegionCategories.dungeon,
    ]
    claim_cost: int = 3

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 3)]

    def campaign_ability_effect_short_text(self) -> str:
        return f"5 {resource_to_emoji(Resource.STRENGTH)}"

    def campaign_ability_effect_full_text(self) -> str:
        return f"Double target campaigning creature {resource_to_emoji(Resource.STRENGTH)} {str(Resource.STRENGTH).lower().title()} (max +5)."

    def campaign_ability_effect(
        self,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: List[Selected] = [],
    ) -> int:
        with creature_db.parent.transaction(parent=con) as con:
            if not extra_data:
                raise MissingExtraData(
                    Choice(
                        0,
                        "Choose a card from your campaign to empower it.",
                        get_cards_in_campaign_options,
                        select_option_by_value,
                    )
                )

            selected_creature = cast(SelectedCreature, extra_data.pop(0))
            s = [
                s for c, s in creature_db.owner.get_campaign(con=con) if c == selected_creature.item
            ][0]
            selected_creature.item.change_strength(s + min(s, 5), con=con)

        return 0


class ArcaneGolem(SimpleCreature):
    id = 30
    name = "arcane golem"
    quest_region_categories: list[RegionCategory] = [RegionCategories.arcane]
    claim_cost: int = 3

    def quest_price(self) -> None:
        return None

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.MAGIC, 5)]

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.STRENGTH, 5)]


class WildDrake(SimpleCreature):
    id = 31
    name = "wild drake"
    quest_region_categories: list[RegionCategory] = [RegionCategories.wild]
    claim_cost: int = 4

    def quest_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 2)]

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 4), Price(Resource.ORDERS, 1)]

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.STRENGTH, 8)]


class Duke(SimpleCreature):
    id = 32
    name = "duke"
    quest_region_categories: list[RegionCategory] = [RegionCategories.noble]
    claim_cost: int = 3

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.GOLD, 3)]

    def campaign_price(self) -> None:
        return None


class Spy(SimpleCreature):
    id = 33
    name = "spy"
    quest_region_categories: list[RegionCategory] = [
        RegionCategories.noble,
        RegionCategories.market,
        RegionCategories.dungeon,
        RegionCategories.arcane,
        RegionCategories.wild,
    ]
    claim_cost: int = 5

    def quest_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 2)]

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.INTEL, 2)]

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 2)]

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.INTEL, 1)]


class Drow(SimpleCreature):
    id = 34
    name = "drow"
    quest_region_categories: list[RegionCategory] = [RegionCategories.dungeon]
    claim_cost: int = 3

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.STRENGTH, 2)]

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 2)]

    def campaign_gain(self) -> List[Gain]:
        return [Gain(Resource.STRENGTH, 4)]


class Alchemist(SimpleCreature):
    id = 35
    name = "alchemist"
    quest_region_categories: list[RegionCategory] = [RegionCategories.arcane]
    claim_cost: int = 5

    def quest_price(self) -> List[Price]:
        return [Price(Resource.MAGIC, 5)]

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.GOLD, 5)]

    def campaign_price(self) -> None:
        return None


class TalkingCat(SimpleCreature):
    id = 36
    name = "talking cat"
    quest_region_categories: list[RegionCategory] = [RegionCategories.market, RegionCategories.wild]

    def quest_ability_effect_short_text(self) -> str:
        return "⤵️"

    def quest_ability_effect_full_text(self) -> str:
        return "Directly returns to your hand after played"

    def campaign_price(self) -> None:
        return None

    def quest_ability_effect(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        with region_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner
            owner.delete_creature_in_played(creature_db, con=con)
            owner.add_creature_to_hand(creature_db, con=con)


class Tavernkeeper(SimpleCreature):
    id = 37
    name = "tavernkeeper"
    quest_region_categories: list[RegionCategory] = [RegionCategories.market]
    claim_cost: int = 3

    def quest_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 3)]

    def quest_ability_effect_short_text(self) -> str:
        return "🍺🔁🔀"

    def quest_ability_effect_full_text(self) -> str:
        return (
            "Return all played creatures to your discard. Then shuffle your discard to your deck."
        )

    def campaign_price(self) -> None:
        return None

    def quest_ability_effect(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        with region_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner
            for c, _ in owner.get_played(con=con):
                owner.delete_creature_in_played(c, con=con)
                owner.add_to_discard(c, con=con)

            owner.reshuffle_discard(con=con)


class Mimic(SimpleCreature):
    id = 38
    name = "mimic"
    quest_region_categories: list[RegionCategory] = [RegionCategories.dungeon]
    claim_cost: int = 4

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.INTEL, 1)]

    def campaign_price(self) -> List[Price]:
        return [Price(Resource.INTEL, 2)]

    def campaign_ability_effect_short_text(self) -> str:
        return "🆓"

    def campaign_ability_effect_full_text(self) -> str:
        return "Gain all quest rewards from target region as if mimic was sent there. Do not pay any of the region's cost."

    def campaign_ability_effect(
        self,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: List[Selected] = [],
    ) -> int:
        with creature_db.parent.transaction(parent=con) as con:
            if not extra_data:
                raise MissingExtraData(
                    Choice(
                        0,
                        "Choose a card from your campaign to empower it.",
                        get_cards_in_campaign_options,
                        select_option_by_value,
                    )
                )

            selected_region = cast(SelectedRegion, extra_data.pop(0))
            selected_region.item.region.quest_effect(
                selected_region.item, creature_db, con=con, extra_data=extra_data
            )

        return 0


class GreatArcaneWyrm(SimpleCreature):
    id = 40
    name = "great arcane wyrm"
    quest_region_categories: list[RegionCategory] = [RegionCategories.arcane, RegionCategories.wild]
    claim_cost: int = 8

    def quest_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 3)]

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.MAGIC, 5)]

    def campaign_price(self) -> List[Price]:
        return []

    def campaign_ability_effect_short_text(self) -> str:
        return f"X {resource_to_emoji(Resource.MAGIC)} → X {resource_to_emoji(Resource.STRENGTH)}"

    def campaign_ability_effect_full_text(self) -> str:
        return f"Spend all your {resource_to_emoji(Resource.MAGIC)} {str(Resource.MAGIC.name).lower().title()}. Gain this much {resource_to_emoji(Resource.STRENGTH)} {str(Resource.STRENGTH.name).lower().title()}."

    def campaign_ability_effect(
        self,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: List[Selected] = [],
    ) -> int:
        with creature_db.parent.transaction(parent=con) as con:
            magic = creature_db.owner.get_resources(con=con)[Resource.MAGIC]
            creature_db.owner.pay_price([Price(Resource.MAGIC, magic)], con=con)
            return magic


class RedDragon(SimpleCreature):
    id = 41
    name = "red dragon"
    quest_region_categories: list[RegionCategory] = [
        RegionCategories.dungeon,
        RegionCategories.wild,
    ]
    claim_cost: int = 8

    def quest_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 3)]

    def quest_gain(self) -> List[Gain]:
        return [Gain(Resource.RALLY, 3)]

    def campaign_price(self) -> List[Price]:
        return []

    def campaign_ability_effect_short_text(self) -> str:
        return f"X {resource_to_emoji(Resource.GOLD)} → X {resource_to_emoji(Resource.STRENGTH)}"

    def campaign_ability_effect_full_text(self) -> str:
        return f"Spend all your {resource_to_emoji(Resource.GOLD)} {str(Resource.GOLD.name).lower().title()}. Gain this much {resource_to_emoji(Resource.STRENGTH)} {str(Resource.STRENGTH.name).lower().title()}."

    def campaign_ability_effect(
        self,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: List[Selected] = [],
    ) -> int:
        with creature_db.parent.transaction(parent=con) as con:
            gold = creature_db.owner.get_resources(con=con)[Resource.GOLD]
            creature_db.owner.pay_price([Price(Resource.GOLD, gold)], con=con)
            return gold


class Saboteur(SimpleCreature):
    id = 42
    name = "saboteur"
    quest_region_categories: list[RegionCategory] = [
        RegionCategories.noble,
        RegionCategories.market,
        RegionCategories.dungeon,
        RegionCategories.arcane,
        RegionCategories.wild,
    ]
    claim_cost: int = 4

    def quest_price(self) -> List[Price]:
        return [Price(Resource.GOLD, 2)]

    def campaign_price(self) -> None:
        return None

    def quest_ability_effect_short_text(self) -> str:
        return f"{resource_changes_to_short_string(self.quest_price())} → 🃏🃏🗑️"

    def quest_ability_effect_full_text(self) -> str:
        return f"{resource_changes_to_string(self.quest_price())}. Destroy all creatures you have currently in played."

    def quest_ability_effect(
        self,
        region_db: Database.Region,
        creature_db: Database.Creature,
        con: Optional[Database.TransactionManager] = None,
        extra_data: EXTRA_DATA = [],
    ) -> None:
        with region_db.parent.transaction(parent=con) as con:
            owner: Database.Player = creature_db.owner
            for c, _ in owner.get_played(con=con):
                owner.delete_creature_in_played(c, con=con)


creatures_list = [
    Servant(),
    Commoner(),
    NoviceAdventurer(),
    NoviceMage(),
    LoyalSquire(),
    Herald(),
    Local(),
    Guide(),
    MagicStudent(),
    Farmer(),
    Ambassador(),
    Trader(),
    Explorer(),
    Mentor(),
    Hunter(),
    Messenger(),
    Towncrier(),
    Quartermaster(),
    ArcaneTutor(),
    Druid(),
    RetiredGeneral(),
    SwordSmith(),
    Scout(),
    Librarian(),
    Nymph(),
    Soldier(),
    Bandit(),
    Paladin(),
    ArcaneGolem(),
    WildDrake(),
    Duke(),
    Spy(),
    Drow(),
    Alchemist(),
    TalkingCat(),
    Tavernkeeper(),
    Mimic(),
    GreatArcaneWyrm(),
    RedDragon(),
    Saboteur(),
]


assert len(set([c.id for c in creatures_list])) == len(creatures_list)

creatures: dict[int, Database.BaseCreature] = {c.id: c for c in creatures_list}

assert all(key == c.id for key, c in creatures.items())
assert len(set([c.id for c in creatures.values()])) == len(creatures)
