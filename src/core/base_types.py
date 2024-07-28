import time
import json
from typing import Union
from enum import Enum
from collections import namedtuple
from contextlib import contextmanager

BASE_HANDS_SIZE = 5


Resource = Enum(
    "Resource",
    ["ORDERS", "GOLD", "ARTEFACTS", "WORKERS", "MAGIC", "RALLY", "STRENGTH"],
)

BaseResources = [
    Resource.ORDERS,
    Resource.GOLD,
    Resource.ARTEFACTS,
    Resource.WORKERS,
    Resource.MAGIC,
    Resource.RALLY,
    Resource.STRENGTH,
]

Price = namedtuple("Price", ["resource", "amount"], defaults=[Resource.GOLD, 0])
Gain = namedtuple("Gain", ["resource", "amount"], defaults=[Resource.GOLD, 0])
Choice = namedtuple("Choice", ["choices"], defaults=[[]])


def resource_to_emoji(resource: Resource) -> str:
    match resource:
        case Resource.ORDERS:
            return "📜"
        case Resource.GOLD:
            return "🪙"
        case Resource.ARTEFACTS:
            return "🔮"
        case Resource.WORKERS:
            return "⚒️"
        case Resource.MAGIC:
            return "✨"
        case Resource.RALLY:
            return "🚩"
        case Resource.STRENGTH:
            return "⚔️"
        case _:
            return "❓"


def resource_change_to_string(resource_change: Union[Price | Gain], third_person=False) -> str:

    change_text = ""

    if third_person:
        if resource_change.resource == Resource.WORKERS and isinstance(resource_change, Price):
            change_text = "uses {0} {1}"
        elif isinstance(resource_change, Gain):
            change_text = "gains {0} {1}"
        elif isinstance(resource_change, Price):
            change_text = "pays {0} {1}"
    else:
        if resource_change.resource == Resource.WORKERS and isinstance(resource_change, Price):
            change_text = "use {0} {1}"
        elif isinstance(resource_change, Gain):
            change_text = "gain {0} {1}"
        elif isinstance(resource_change, Price):
            change_text = "pay {0} {1}"

    resource_text = resource_change.resource.name.lower()

    if resource_change.amount == 1 and resource_text.endswith("s"):
        resource_text = resource_text[:-1]

    return change_text.format(
        resource_change.amount, resource_to_emoji(resource_change.resource) + resource_text
    )


def resource_changes_to_string(resource_changes: list[Price | Gain], third_person=False) -> str:
    resource_changes = [
        resource_change for resource_change in resource_changes if resource_change.amount != 0
    ]

    prices = [
        resource_change
        for resource_change in resource_changes
        if isinstance(resource_change, Price)
    ]
    gains = [
        resource_change for resource_change in resource_changes if isinstance(resource_change, Gain)
    ]

    price_text = ", ".join(
        [
            resource_change_to_string(resource_change, third_person=third_person)
            for resource_change in prices
        ]
    )
    gains_text = ", ".join(
        [
            resource_change_to_string(resource_change, third_person=third_person)
            for resource_change in gains
        ]
    )

    if len(price_text) == 0 and len(gains_text) == 0:
        return ""
    if len(price_text) == 0:
        return f"{gains_text}"
    if len(gains_text) == 0:
        return f"{price_text}"

    return f"{price_text}. {gains_text}."


def resource_change_to_short_string(resource_change: Union[Price | Gain]) -> str:
    if isinstance(resource_change, Gain):
        change_text = "+{0}{1}"
    elif isinstance(resource_change, Price):
        change_text = "-{0}{1}"

    return change_text.format(resource_change.amount, resource_to_emoji(resource_change.resource))


def resource_changes_to_short_string(resource_changes: list[Price | Gain]) -> str:
    resource_changes = [
        resource_change for resource_change in resource_changes if resource_change.amount != 0
    ]

    prices = [
        resource_change
        for resource_change in resource_changes
        if isinstance(resource_change, Price)
    ]
    gains = [
        resource_change for resource_change in resource_changes if isinstance(resource_change, Gain)
    ]

    price_text = ", ".join(
        [resource_change_to_short_string(resource_change) for resource_change in prices]
    )
    gains_text = ", ".join(
        [resource_change_to_short_string(resource_change) for resource_change in gains]
    )

    if len(price_text) == 0 and len(gains_text) == 0:
        return ""
    if len(price_text) == 0:
        return f"{gains_text}"
    if len(gains_text) == 0:
        return f"{price_text}"

    return f"{price_text} -> {gains_text}"


RegionCategory = namedtuple("RegionCategory", ["name", "emoji"], defaults=["default_region", " "])


class BaseRegion:

    id = -1
    name = "default_region"
    category = None

    def __init__(self):
        pass

    def __repr__(self) -> str:
        return f"<BaseRegion: {self.id}#{self.name}>"

    def __eq__(self, other) -> bool:
        if isinstance(other, BaseRegion):
            return self.id == other.id
        return False

    def quest_effect_short_text(self) -> str:
        return ""

    def quest_effect_full_text(self) -> str:
        return ""

    def quest_effect_price(self, region_db, creature_db, con=None, extra_data={}):
        return

    def quest_effect(self, region_db, creature_db, con=None, extra_data={}):
        return


class BaseCreature:

    id = -1
    name = "default_creature"
    quest_region_categories: list[RegionCategory] = []
    claim_cost: int = 0

    def __init__(self):
        pass

    def __repr__(self) -> str:
        return f"<BaseCreature: {self.name}>"

    def __eq__(self, other) -> bool:
        if isinstance(other, BaseCreature):
            return str(self) == str(other)
        return False

    # questing
    def quest_ability_effect_short_text(self) -> str:
        return ""

    def quest_ability_effect_full_text(self) -> str:
        return ""

    def quest_ability_effect_price(self, region_db, creature_db, con=None, extra_data={}):
        return

    def quest_ability_effect(self, region_db, creature_db, con=None, extra_data={}):
        return

    # campaigning
    def campaign_ability_effect_short_text(self) -> str:
        return ""

    def campaign_ability_effect_full_text(self) -> str:
        return ""

    def campaign_ability_effect_price(self, creature_db, con=None, extra_data={}):
        return

    def campaign_ability_effect(self, creature_db, con=None, extra_data={}):
        return


class StartCondition:

    def __init__(
        self,
        start_config: dict,
        start_active_regions: list[BaseRegion],
        start_available_creatures: list[BaseCreature],
        start_deck: list[BaseCreature],
    ):
        self.start_config = start_config
        self.start_active_regions = start_active_regions
        self.start_available_creatures = start_available_creatures
        self.start_deck = start_deck


class Event:

    event_type = "base_event"

    def __init__(self, parent, id: int, timestamp: int, parent_event, guild):
        self.parent = parent
        self.id = id
        self.timestamp = timestamp
        self.parent_event = parent_event
        self.guild = guild

    def __repr__(self) -> str:
        return f"<event: {self.event_type}#{self.id}, timestamp: {self.timestamp}, {self.text()}>"

    def __eq__(self, other) -> bool:
        if isinstance(other, Event):
            return self.id == other.id
        return False

    def from_extra_data(parent, id: int, timestamp: int, parent_event, guild, extra_data: dict):
        return Event(parent, id, timestamp, parent_event, guild)

    def extra_data(self) -> str:
        return json.dumps({})

    def text(self) -> str:
        return ""

    def resolve(self, con=None):
        pass
