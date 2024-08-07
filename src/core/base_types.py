from __future__ import annotations
import time
import json

from typing import Union, Any, Optional
from enum import Enum
from collections import namedtuple
from contextlib import contextmanager

BASE_HANDS_SIZE = 5


Resource = Enum(
    "Resource",
    ["ORDERS", "GOLD", "ARTEFACTS", "INTEL", "MAGIC", "RALLY", "STRENGTH"],
)

BaseResources = [
    Resource.ORDERS,
    Resource.GOLD,
    Resource.ARTEFACTS,
    Resource.INTEL,
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
        case Resource.INTEL:
            return "🤫"
        case Resource.MAGIC:
            return "✨"
        case Resource.RALLY:
            return "🚩"
        case Resource.STRENGTH:
            return "⚔️"


def resource_change_to_string(
    resource_change: Union[Price | Gain], third_person: bool = False
) -> str:

    change_text = ""

    if third_person:
        if isinstance(resource_change, Gain):
            change_text = "gains {0} {1}"
        elif isinstance(resource_change, Price):
            change_text = "pays {0} {1}"
    else:
        if isinstance(resource_change, Gain):
            change_text = "gain {0} {1}"
        elif isinstance(resource_change, Price):
            change_text = "pay {0} {1}"

    resource_text = resource_change.resource.name.lower()

    if resource_change.amount == 1 and resource_text.endswith("s"):
        if resource_text.endswith("ies"):
            resource_text = resource_text[:-3] + "y"
        else:
            resource_text = resource_text[:-1]

    return change_text.format(
        resource_change.amount, resource_to_emoji(resource_change.resource) + resource_text
    )


def resource_changes_to_string(
    resource_changes: list[Price | Gain], third_person: bool = False
) -> str:
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


class Event:

    event_type = "base_event"

    def __init__(
        self,
        parent: Any,
        id: int,
        timestamp: float,
        parent_event: Optional[Event],
        guild: Any,
    ):
        self.parent = parent
        self.id = id
        self.timestamp = timestamp
        self.parent_event = parent_event
        self.guild = guild

    def __repr__(self) -> str:
        return f"<event: {self.event_type}#{self.id}, timestamp: {self.timestamp}, {self.text()}>"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Event):
            return self.id == other.id
        return False

    @staticmethod
    def from_extra_data(
        parent: Any,
        id: int,
        timestamp: int,
        parent_event: Event,
        guild: Any,
        extra_data: dict[Any, Any],
    ) -> Event:
        return Event(parent, id, timestamp, parent_event, guild)

    def extra_data(self) -> str:
        assert False

    def text(self) -> str:
        assert False

    def resolve(self, con: Any) -> None:
        return
