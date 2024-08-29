from __future__ import annotations
from typing import Optional, Any, List, Tuple, cast, NamedTuple, Callable

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
    RegionCategories,
    region_categories,
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


class Choice(NamedTuple):
    timestamp: int
    text: str
    get_options: Callable[[Database.Player, Optional[Database.TransactionManager]], List[Selected]]
    select_option: Callable[
        [Database.Player, Choice, int, Optional[Database.TransactionManager]], Selected
    ]


class SelectedChoice(Selected):
    def __init__(self, item: int, text_info: str) -> None:
        super().__init__(item)
        self.text_info = text_info

    def text(self) -> str:
        return self.text_info

    def value(self) -> int:
        return cast(int, self.item)


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


class SelectedRegionCategory(Selected):
    def __init__(self, item: RegionCategory) -> None:
        super().__init__(item)
        self.item = item

    def text(self) -> str:
        return (
            str(cast(RegionCategory, self.item).emoji)
            + " "
            + str(cast(RegionCategory, self.item).name)
        )

    def value(self) -> int:
        return int(cast(RegionCategory, self.item).id)


def get_cards_in_hand_options(
    player_db: Database.Player, con: Optional[Database.TransactionManager]
) -> List[Selected]:
    return [cast(Selected, SelectedCreature(c)) for c in player_db.get_hand(con=con)]


def get_cards_in_deck_options(
    player_db: Database.Player, con: Optional[Database.TransactionManager]
) -> List[Selected]:
    return [cast(Selected, SelectedCreature(c)) for c in player_db.get_deck(con=con)]


def get_cards_in_discard_options(
    player_db: Database.Player, con: Optional[Database.TransactionManager]
) -> List[Selected]:
    return [cast(Selected, SelectedCreature(c)) for c in player_db.get_discard(con=con)]


def get_cards_in_played_options(
    player_db: Database.Player, con: Optional[Database.TransactionManager]
) -> List[Selected]:
    return [
        cast(Selected, SelectedPlayedCreature((c, v))) for c, v in player_db.get_played(con=con)
    ]


def get_cards_in_campaign_options(
    player_db: Database.Player, con: Optional[Database.TransactionManager]
) -> List[Selected]:
    return [
        cast(Selected, SelectedCampaignCreature((c, s))) for c, s in player_db.get_campaign(con=con)
    ]


def get_regions_options(
    player_db: Database.Player, con: Optional[Database.TransactionManager]
) -> List[Selected]:
    return [cast(Selected, SelectedRegion(r)) for r in player_db.guild.get_regions(con=con)]


def get_region_categories_options(
    player_db: Database.Player, con: Optional[Database.TransactionManager]
) -> List[Selected]:
    return [cast(Selected, SelectedRegionCategory(r)) for r in region_categories]


def select_option_by_value(
    player_db: Database.Player,
    c: Choice,
    v: int,
    con: Optional[Database.TransactionManager],
) -> Selected:
    return [s for s in c.get_options(player_db, con) if s.value() == v][0]


EXTRA_DATA = List[Selected]


class MissingExtraData(commands.UserInputError):
    def __init__(self, choice: Choice):
        super().__init__(choice.text)
        self.choice = choice

    def __str__(self) -> str:
        return f"{super().__str__()} with Choice {self.choice})"


class BadExtraData(commands.UserInputError):
    def __init__(self, message: str = "", extra_data: EXTRA_DATA = []):
        super().__init__(message)
        self.extra_data = extra_data

    def __str__(self) -> str:
        if self.extra_data:
            return f"{super().__str__()} (Extra data: {self.extra_data})"
        return super().__str__()
