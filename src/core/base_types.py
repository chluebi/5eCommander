import time
from typing import Union
from enum import Enum
from collections import namedtuple, defaultdict
from contextlib import contextmanager

BASE_HANDS_SIZE = 5


class GuildNotFound(Exception):
    pass


class PlayerNotFound(Exception):
    pass


class CreatureNotFound(Exception):
    pass


class RegionNotFound(Exception):
    pass


class NotEnoughResourcesException(Exception):
    pass


class EmptyDeckException(Exception):
    pass


class MissingExtraData(Exception):

    def __init__(self, message="", extra_data=None):
        super().__init__(message)
        self.extra_data = extra_data if extra_data is not None else {}

    def __str__(self):
        if self.extra_data:
            return f"{super().__str__()} (Extra data: {self.extra_data})"
        return super().__str__()


class BadExtraData(Exception):

    def __init__(self, message="", extra_data=None):
        super().__init__(message)
        self.extra_data = extra_data if extra_data is not None else {}

    def __str__(self):
        if self.extra_data:
            return f"{super().__str__()} (Extra data: {self.extra_data})"
        return super().__str__()


class CreatureCannotQuestHere(Exception):
    pass


class ProtectedFreeCreature(Exception):
    pass


class ExpiredFreeCreature(Exception):
    pass


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

OptionalEffect = namedtuple("OptionalEffect", ["price", "gain"], defaults=[[], []])


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


def resource_change_to_string(resource_change: Union[Price | Gain]) -> str:

    change_text = ""
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


def resource_changes_to_string(resource_changes: list[Price | Gain]) -> str:
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
        [resource_change_to_string(resource_change) for resource_change in prices]
    )
    gains_text = ", ".join(
        [resource_change_to_string(resource_change) for resource_change in gains]
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

    def __init__(self, parent, id: int, timestamp: int, guild):
        self.parent = parent
        self.id = id
        self.timestamp = timestamp
        self.guild = guild

    def resolve(self, con=None):
        pass


class Database:

    def __init__(self, start_condition: StartCondition):
        self.start_condition = start_condition

    def timestamp_after(self, seconds: int):
        return int(time.time() + seconds)

    def start_connection(self):
        pass

    def end_connection(self, con):
        pass

    def commit_connection(self, con):
        pass

    def rollback_connection(self, con):
        pass

    class TransactionManager:

        def __init__(self, parent, con, trans):
            self.parent = parent
            self.con = con
            self.trans = trans

        def __enter__(self):
            return self.con

        def __exit__(self, exc_type, exc_value, traceback):
            if self.trans is None:
                if exc_type is not None:
                    return False
                return True
            else:
                if exc_type is not None:
                    self.parent.rollback_transaction(self.trans)
                    return False

                self.parent.commit_transaction(self.trans)
                return True

    def transaction(self, con=None):
        is_top = con is None
        trans = None
        if con is None:
            con, trans = self.start_connection()

        return Database.TransactionManager(self, con, trans)

    def fresh_event_id(self, guild, con=None):
        pass

    def add_event(self, event: Event, con=None):
        pass

    def get_events(self, timestamp_start: int, timestamp_end: int, con=None):
        pass

    def add_guild(self, guild_id: int, con=None):
        pass

    def get_guilds(self, con=None):
        pass

    def get_guild(self, guild_id: int, con=None):
        pass

    def remove_guild(self, guild_id: int, con=None):
        pass

    class Guild:

        def __init__(self, parent, id: int):
            self.parent = parent
            self.id = id

        def __eq__(self, other) -> bool:
            if isinstance(other, Database.Guild):
                return self.parent == other.parent and self.id == other.id
            return False

        def __repr__(self) -> str:
            return f"<DatabaseGuild: {self.id}>"

        def set_config(self, config: dict, con=None):
            pass

        def get_config(self, con=None):
            pass

        def fresh_region_id(self, con=None):
            pass

        def add_region(self, region: BaseRegion, con=None):
            pass

        def get_regions(self, con=None):
            pass

        def get_region(self, region: BaseRegion, con=None):
            pass

        def remove_region(self, region: BaseRegion, con=None):
            pass

        def add_player(self, player_id: int, con=None):
            pass

        def get_players(self):
            pass

        def get_player(self, player_id: int, con=None):
            pass

        def remove_player(self, player, con=None):
            pass

        def fresh_creature_id(self, con=None):
            pass

        def add_creature(self, creature: BaseCreature, owner, con=None):
            pass

        def get_creatures(self, con=None):
            pass

        def get_creature(self, creature_id: int, con=None):
            pass

        def remove_creature(self, creature, con=None):
            pass

        def add_to_creature_pool(self, creature: BaseCreature, con=None):
            pass

        def get_creature_pool(self, con=None):
            pass

        def get_random_from_creature_pool(self, con=None):
            pass

        def remove_from_creature_pool(self, creature: BaseCreature, con=None):
            pass

        def add_free_creature(
            self, creature: BaseCreature, channel_id: int, message_id: int, roller, con=None
        ):
            pass

        def get_free_creatures(self, con=None):
            pass

        def get_free_creature(self, channel_id: int, message_id: int, con=None):
            pass

        def remove_free_creature(self, creature, con=None):
            pass

    class Region:

        def __init__(self, parent, id: int, region: BaseRegion, guild):
            self.parent = parent
            self.id = id
            self.region = region
            self.guild = guild

        def __eq__(self, other) -> bool:
            if isinstance(other, Database.Region):
                return (
                    self.parent == other.parent
                    and self.id == other.id
                    and self.guild.id == other.guild.id
                )
            return False

        def __repr__(self) -> str:
            return f"<DatabaseRegion: {self.region} in {self.guild}, status: {self.occupied()}>"

        def occupy(self, creature, con=None):
            pass

        def unoccupy(self, current: int, con=None):
            pass

        def occupied(self, con=None) -> tuple:
            pass

        class RegionRechargeEvent(Event):

            def __init__(self, parent, id: int, guild, timestamp: int, region):
                super().__init__(parent, id, timestamp, guild)
                self.region = region

            def resolve(self, con=None):
                self.region.unoccupy(self.timestamp, con=con)

    class Player:

        def __init__(self, parent, id, guild):
            self.parent = parent
            self.id = id
            self.guild = guild

        def __eq__(self, other) -> bool:
            if isinstance(other, Database.Player):
                return (
                    self.parent == other.parent
                    and self.guild.id == other.guild.id
                    and self.id == other.id
                )
            return False

        def __repr__(self) -> str:
            return f"<DatabasePlayer: {self.id} in {self.guild}>"

        def get_resources(self, con=None) -> dict[Resource, int]:
            pass

        def set_resources(self, resources: dict[Resource, int], con=None):
            pass

        def get_deck(self, con=None):
            pass

        def get_hand(self, con=None):
            pass

        def get_discard(self, con=None):
            pass

        def get_full_deck(self, con=None):
            with self.parent.transaction(con=con) as con:
                return sorted(
                    self.get_deck(con=con) + self.get_hand(con=con) + self.get_discard(con=None),
                    key=lambda x: str(x),
                )

        def has(self, resource: Resource, amount: int, con=None) -> bool:
            return self.fulfills_price([Price(resource, amount)], con=con)

        def give(self, resource: Resource, amount: int, con=None) -> None:
            self.gain([Gain(resource, amount)], con=con)

        def remove(self, resource: Resource, amount: int, con=None) -> None:
            self.give(resource, -amount, con=con)

        def fulfills_price(self, price: list[Price], con=None) -> bool:
            merged_prices = defaultdict(lambda: 0)
            for p in price:
                if p.amount == 0:
                    continue

                merged_prices[p.resource] += p.amount

            if len(merged_prices) == 0:
                return True

            with self.parent.transaction(con=con) as con:
                resources: dict[Resource, int] = self.get_resources(con=con)
                hand_size: list = len(self.get_hand(con=con))

            for r, a in merged_prices.items():
                if r in BaseResources:
                    if resources[r] < a:
                        return False
                elif r == Resource.DELETE_CREATURES:
                    if hand_size < a:
                        return False
            return True

        def _delete_creatures(self, hand_size: int, a: int, extra_data: dict, con=None):

            expected_extra_data = {
                "creatures_to_delete": {"text": "creatures to delete", "type": "list creature"}
            }

            try:
                creatures_to_delete = extra_data["creatures_to_delete"]
            except KeyError:
                raise MissingExtraData(extra_data=expected_extra_data)

            try:
                assert len(set(creatures_to_delete)) >= a
                for creature_id in creatures_to_delete:
                    assert self.guild.get_creature(creature_id, con=con).owner == self
            except Exception as e:
                BadExtraData(str(e), extra_data=expected_extra_data)

            # like this extra_data can be further propagated
            creatures_to_delete = creatures_to_delete[:a]
            extra_data["creatures_to_delete"] = creatures_to_delete

            with self.parent.transaction(con=con) as con:
                for c in creatures_to_delete:
                    self.delete_creature_from_hand(c)

        def gain(self, gain: list[Gain], con=None, extra_data={}) -> None:
            merged_gains = defaultdict(lambda: 0)
            for g in gain:
                if g.amount == 0:
                    continue
                merged_gains[g.resource] += g.amount

            if len(merged_gains) == 0:
                return

            with self.parent.transaction(con=con) as con:

                resources: dict[Resource, int] = self.get_resources(con=con)
                hand_size: list = len(self.get_hand(con=con))

                for r, a in merged_gains.items():
                    if r in BaseResources:
                        resources[r] += a
                    elif r == Resource.CREATURES_IN_HAND:
                        self.draw_cards(N=a, con=con)
                    elif r == Resource.DELETE_CREATURES:
                        self._delete_creatures(hand_size, a, extra_data, con=con)

                self.set_resources(resources, con=con)

        def pay_price(self, price: list[Price], con=None, extra_data={}) -> None:
            merged_price = defaultdict(lambda: 0)
            for p in price:
                if p.amount == 0:
                    continue
                merged_price[p.resource] += p.amount

            if len(merged_price) == 0:
                return

            with self.parent.transaction(con=con) as con:

                resources: dict[Resource, int] = self.get_resources(con=con)
                hand_size: list = len(self.get_hand(con=con))

                for r, a in merged_price.items():
                    if r in BaseResources:
                        if resources[r] < a:
                            raise NotEnoughResourcesException(
                                "Player is paying {} {} but only has {}".format(a, r, resources[r])
                            )
                        resources[r] -= a
                    elif r == Resource.DELETE_CREATURES:
                        self._delete_creatures(hand_size, a, extra_data, con=con)
                self.set_resources(resources, con=con)

        def draw_card_raw(self, con=None) -> BaseCreature:
            pass

        def reshuffle_discard(self, con=None) -> None:
            pass

        def draw_cards(self, N=1, con=None) -> tuple[int, bool]:
            with self.parent.transaction(con=con) as con:
                cards_drawn = []
                discard_reshuffled = False
                for _ in range(N):
                    if len(self.get_deck(con=con)) == 0:
                        self.reshuffle_discard(con=con)
                        discard_reshuffled = True

                        if len(self.get_deck(con=con)) == 0:
                            return cards_drawn, discard_reshuffled

                    card = self.draw_card_raw(con=con)
                    cards_drawn.append(card)

                return cards_drawn, discard_reshuffled

        def delete_creature_from_hand(self, creature, con=None) -> None:
            pass

        def play_creature(self, creature, con=None) -> None:
            pass

        def add_to_discard(self, creature, con=None) -> None:
            pass

        def play_creature_to_region(self, creature, region, con=None, extra_data={}):

            if region.region.category not in creature.creature.quest_region_categories:
                raise CreatureCannotQuestHere(
                    f"Region is {region.region.category} but creature can only go to {creature.creature.quest_region_categories}"
                )

            base_region: BaseRegion = region.region
            base_creature: BaseCreature = creature.creature

            with self.parent.transaction(con=con) as con:
                self.pay_price([Price(Resource.ORDERS, 1)], con=con)
                base_creature.quest_ability_effect_price(
                    region, creature, con=con, extra_data=extra_data
                )
                base_region.quest_effect_price(region, creature, con=con, extra_data=extra_data)
                self.play_creature(creature, con=con)
                region: Database.Region = region
                region.occupy(creature, con=con)
                creature.play(con=con)
                base_region.quest_effect(region, creature, con=con, extra_data=extra_data)
                base_creature.quest_ability_effect(region, creature, con=con, extra_data=extra_data)

        def play_creature_to_campaign(self, creature, con=None, extra_data={}):

            base_creature: BaseCreature = creature.creature

            with self.parent.transaction(con=con) as con:
                base_creature.campaign_ability_effect_price(
                    creature, con=con, extra_data=extra_data
                )
                self.play_creature(creature, con=con)
                base_creature.campaign_ability_effect(creature, con=con, extra_data=extra_data)

    class Creature:

        def __init__(self, parent, id: int, creature: BaseCreature, guild, owner):
            self.parent = parent
            self.id = id
            self.creature = creature
            self.guild = guild
            self.owner = owner

        def __eq__(self, other) -> bool:
            if isinstance(other, Database.Creature):
                return (
                    self.parent == other.parent
                    and self.guild.id == other.guild.id
                    and self.id == other.id
                )
            return False

        def __repr__(self) -> str:
            return f"<DatabaseCreature: {self.creature} in {self.guild} as {self.id} owned by {self.owner}>"

        def play(self, con=None):
            with self.parent.transaction(con=con) as con:
                until = self.parent.timestamp_after(self.guild.get_config()["creature_recharge"])

                self.parent.add_event(
                    Database.Creature.CreatureRechargeEvent(
                        self.parent,
                        self.parent.fresh_event_id(self.guild, con=con),
                        self.guild,
                        until,
                        self,
                    ),
                    con=con,
                )

        class CreatureRechargeEvent(Event):

            def __init__(self, parent, id: int, guild, timestamp: int, creature):
                super().__init__(parent, id, timestamp, guild)
                self.creature = creature

            def resolve(self, con=None):
                self.creature.owner.add_to_discard(self.creature, con=con)

    class FreeCreature:

        def __init__(
            self,
            parent,
            creature: BaseCreature,
            guild,
            channel_id: int,
            message_id: int,
            roller,
            timestamp_protected: int,
            timestamp_expires: int,
        ):
            self.parent = parent
            self.guild = guild
            self.creature = creature
            self.roller = roller
            self.channel_id = channel_id
            self.message_id = message_id

        def __eq__(self, other) -> bool:
            if isinstance(other, Database.FreeCreature):
                return (
                    self.parent == other.parent
                    and self.creature == other.creature
                    and self.guild.id == other.guild.id
                    and self.channel_id == other.channel_id
                    and self.message_id == other.message_id
                )
            return False

        def get_protected_timestamp(self, con=None) -> int:
            pass

        def get_expires_timestamp(self, con=None) -> int:
            pass

        def is_protected(self, timestamp: int, con=None) -> bool:
            return self.get_protected_timestamp(con=con) > timestamp

        def is_expired(self, timestamp: int, con=None) -> bool:
            return self.get_expires_timestamp(con=con) < timestamp

        def claimed(self, con=None):
            pass

        def claim(self, timestamp: int, owner, con=None):

            owner: Database.Player = owner
            guild: Database.Guild = self.guild

            guild.get_free_creature(self.channel_id, self.message_id)

            if self.is_expired(timestamp):
                raise ExpiredFreeCreature()

            if self.is_protected(timestamp) and owner != self.roller:
                raise ProtectedFreeCreature(
                    f"This creature is protected until {self.get_protected_timestamp()}"
                )

            with self.parent.transaction(con=con) as con:
                owner.pay_price([Price(Resource.RALLY, self.creature.claim_cost)], con=con)
                guild.remove_free_creature(self, con=con)
                guild.add_creature(self.creature, owner, con=con)
                self.claimed(con=con)

        class FreeCreatureProtectedEvent(Event):

            def __init__(self, parent, id: int, guild, timestamp: int, free_creature):
                super().__init__(parent, id, timestamp, guild)
                self.free_creature = free_creature

        class FreeCreatureExpiresEvent(Event):

            def __init__(self, parent, id: int, guild, timestamp: int, free_creature):
                super().__init__(parent, id, timestamp, guild)
                self.free_creature = free_creature

            def resolve(self, con=None):
                self.guild.remove_free_creature(self.free_creature, con=con)
