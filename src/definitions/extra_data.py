from typing import Optional, Any, List, Tuple, cast, NamedTuple

from enum import Enum
from collections import namedtuple

from discord.ext import commands

from src.core.base_types import (
    Resource,
    Price,
    Gain,
    RegionCategory,
    Selected,
    resource_changes_to_string,
    resource_changes_to_short_string,
    resource_to_emoji,
)
from src.core.exceptions import CreatureNotFound
from src.database.database import Database

ExtraDataCategory = Enum(
    "ExtraDataCategory",
    [
        "CHOICES",
        "CREATURES_IN_HAND",
        "CREATURES_IN_DECK",
        "CREATURES_IN_DISCARD",
        "CREATURES_IN_PLAYED",
        "CREATURES_IN_CAMPAIGN",
        "REGIONS",
    ],
)


class SelectedChoice(Selected):
    def __init__(self, item: int, text_info: str) -> None:
        super().__init__(item)
        self.text_info = text_info

    def text(self) -> str:
        return self.text_info

    def value(self) -> int:
        return cast(int, self.item)


class Choice(NamedTuple):
    timestamp: int
    text: str
    category: ExtraDataCategory
    options: List[SelectedChoice]


class SelectedCreature(Selected):
    def __init__(self, item: Database.Creature) -> None:
        super().__init__(item)
        self.item = item

    def text(self) -> str:
        return cast(Database.Creature, self.item).text()

    def value(self) -> int:
        return cast(Database.Creature, self.item).id


class SelectedPlayedCreature(Selected):
    def __init__(self, item: Tuple[Database.Creature, int]) -> None:
        super().__init__(item)
        self.item = item

    def text(self) -> str:
        return cast(Database.Creature, self.item[0]).text()

    def value(self) -> int:
        return cast(Database.Creature, self.item[0]).id


class SelectedCampaignCreature(Selected):
    def __init__(self, item: Tuple[Database.Creature, int]) -> None:
        super().__init__(item)
        self.item = item

    def text(self) -> str:
        return f"{cast(Database.Creature, self.item[0]).text()}: {self.item[1]} {resource_to_emoji(Resource.STRENGTH)}"

    def value(self) -> int:
        return cast(Database.Creature, self.item[0]).id


class SelectedRegion(Selected):
    def __init__(self, item: Database.Region) -> None:
        super().__init__(item)
        self.item = item

    def text(self) -> str:
        return cast(Database.Region, self.item).text()

    def value(self) -> int:
        return cast(Database.Region, self.item).id


EXTRA_DATA = Optional[dict[ExtraDataCategory, List[Selected]]]


def fetch_from_category(
    player_db: Database.Player,
    cat: ExtraDataCategory,
    con: Optional[Database.TransactionManager] = None,
) -> List[Selected]:
    match cat:
        case ExtraDataCategory.CHOICES:
            assert False
        case ExtraDataCategory.CREATURES_IN_HAND:
            return [SelectedCreature(c) for c in player_db.get_hand(con=con)]
        case ExtraDataCategory.CREATURES_IN_DECK:
            return [SelectedCreature(c) for c in player_db.get_deck(con=con)]
        case ExtraDataCategory.CREATURES_IN_DISCARD:
            return [SelectedCreature(c) for c in player_db.get_discard(con=con)]
        case ExtraDataCategory.CREATURES_IN_PLAYED:
            return [SelectedPlayedCreature(c) for c in player_db.get_played(con=con)]
        case ExtraDataCategory.CREATURES_IN_CAMPAIGN:
            return [SelectedCampaignCreature(c) for c in player_db.get_campaign(con=con)]
        case ExtraDataCategory.REGIONS:
            return [SelectedRegion(r) for r in player_db.guild.get_regions(con=con)]


def get_selected_from_int(
    player_db: Database.Player,
    choice: Choice,
    v: int,
    con: Optional[Database.TransactionManager] = None,
) -> Selected:
    match choice.category:
        case ExtraDataCategory.CHOICES:
            return choice.options[v]
        case ExtraDataCategory.CREATURES_IN_HAND:
            return SelectedCreature(player_db.guild.get_creature(v, con=con))
        case ExtraDataCategory.CREATURES_IN_DECK:
            return SelectedCreature(player_db.guild.get_creature(v, con=con))
        case ExtraDataCategory.CREATURES_IN_DISCARD:
            return SelectedCreature(player_db.guild.get_creature(v, con=con))
        case ExtraDataCategory.CREATURES_IN_PLAYED:
            played = player_db.get_played(con=con)
            for c, t in played:
                if c.id == v:
                    return SelectedPlayedCreature((c, t))
            raise CreatureNotFound()
        case ExtraDataCategory.CREATURES_IN_CAMPAIGN:
            campaign = player_db.get_campaign(con=con)
            for c, s in campaign:
                if c.id == v:
                    return SelectedCampaignCreature((c, s))
            raise CreatureNotFound()
        case ExtraDataCategory.REGIONS:
            return SelectedRegion(player_db.guild.get_region(v, con=con))


class MissingExtraData(commands.UserInputError):
    def __init__(self, choice: Choice):
        super().__init__(choice.text)
        self.choice = choice

    def __str__(self) -> str:
        return f"{super().__str__()} with Choice {self.choice})"


class BadExtraData(commands.UserInputError):
    def __init__(self, message: str = "", extra_data: EXTRA_DATA = None):
        super().__init__(message)
        self.extra_data = extra_data if extra_data is not None else {}

    def __str__(self) -> str:
        if self.extra_data:
            return f"{super().__str__()} (Extra data: {self.extra_data})"
        return super().__str__()
