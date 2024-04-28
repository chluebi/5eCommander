import time
from typing import Union
from enum import Enum
from collections import namedtuple, defaultdict

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


class NoCreaturesToDeleteProvided(Exception):
    pass


class CreatureCannotQuestHere(Exception):
    pass


class ProtectedFreeCreature(Exception):
    pass


class ExpiredFreeCreature(Exception):
    pass


Resource = Enum(
    "Resource",
    [
        "ORDERS",
        "GOLD",
        "ARTEFACTS",
        "WORKERS",
        "MAGIC",
        "RALLY",
        "STRENGTH",
        "CREATURES_IN_HAND",
        "DELETE_CREATURES",
    ],
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
        case Resource.CREATURES_IN_HAND:
            return "🃏"
        case Resource.DELETE_CREATURES:
            return "❎"
        case _:
            return "❓"


def r_change_to_string(r_change: Union[Price | Gain]) -> str:

    change_text = ""
    if r_change.resource == Resource.CREATURES_IN_HAND:
        if isinstance(r_change, Price):
            change_text = "draw {0} {1}"
        else:
            raise Exception("Creatures in hand can only be drawn not lost")
    elif r_change.resource == Resource.DELETE_CREATURES:
        change_text = "delete {0} {1} from your hand"
    elif r_change.resource == Resource.WORKERS and isinstance(r_change, Price):
        change_text = "use {0} {1}"
    elif isinstance(r_change, Gain):
        change_text = "gain {0} {1}"
    elif isinstance(r_change, Price):
        change_text = "pay {0} {1}"

    resource_text = ""
    if r_change.resource == Resource.CREATURES_IN_HAND:
        resource_text = "creatures"
    elif r_change.resource == Resource.DELETE_CREATURES:
        resource_text = "creatures"
    else:
        resource_text = r_change.resource.name.lower()

    if r_change.amount == 1 and resource_text.endswith("s"):
        resource_text = resource_text[:-1]

    return change_text.format(r_change.amount, resource_to_emoji(r_change.resource) + resource_text)


def r_changes_to_string(r_changes: list[Price | Gain]) -> str:
    r_changes = [r_change for r_change in r_changes if r_change.amount != 0]

    prices = [r_change for r_change in r_changes if isinstance(r_change, Price)]
    gains = [r_change for r_change in r_changes if isinstance(r_change, Gain)]

    price_text = ", ".join([r_change_to_string(r_change) for r_change in prices])
    gains_text = ", ".join([r_change_to_string(r_change) for r_change in gains])

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

    def quest_effect_text(self) -> str:
        price, gains = self.quest_effect()
        return r_changes_to_string(price + gains)

    def quest_effect(self) -> tuple[list[Price], list[Gain]]:
        return [], []


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
    def quest_ability_effect_text(self) -> str:
        price, gains = self.quest_ability_effect()
        return r_changes_to_string(price + gains)

    def quest_ability_effect(self) -> tuple[list[Price], list[Gain]]:
        return [], []

    # campaigning
    def campaign_ability_effect_text(self) -> str:
        price, gains = self.campaign_ability_effect()
        return r_changes_to_string(price + gains)

    def campaign_ability_effect(self) -> tuple[list[Price], list[Gain]]:
        return [], []


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

    def __init__(self, id: int, parent, timestamp: int, guild):
        self.id = id
        self.parent = parent
        self.timestamp = timestamp
        self.guild = guild

    def resolve(self):
        pass


class Database:

    def __init__(self, start_condition: StartCondition):
        self.start_condition = start_condition

    def timestamp_after(self, seconds: int):
        return int(time.time() + seconds)

    def start_transaction(self):
        pass

    def end_transaction(self):
        pass

    class Transaction:

        def __init__(self, parent, in_trans=False):
            self.parent = parent
            self.in_trans = in_trans

        def __enter__(self):
            if not self.in_trans:
                self.parent.start_transaction()
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            if exc_type is not None and not self.in_trans:
                self.parent.end_transaction()

    def fresh_event_id(self, guild):
        pass

    def add_event(self, event: Event):
        pass

    def get_events(self, timestamp_start: int, timestamp_end: int):
        pass

    def add_guild(self, guild_id: int):
        pass

    def get_guilds(self):
        pass

    def get_guild(self, guild_id: int):
        pass

    def remove_guild(self, guild_id: int):
        pass

    class Guild:

        def __init__(self, parent, id: int, start_condition: StartCondition):
            self.parent = parent
            self.id = id

        def __eq__(self, other) -> bool:
            if isinstance(other, Database.Guild):
                return self.parent == other.parent and self.id == other.id
            return False

        def __repr__(self) -> str:
            return f"<DatabaseGuild: {self.id}>"

        def set_config(self, config: dict):
            pass

        def get_config(self):
            pass

        def fresh_region_id(self):
            pass

        def add_region(self, region: BaseRegion):
            pass

        def get_regions(self):
            pass

        def get_region(self, region: BaseRegion):
            pass

        def remove_region(self, region: BaseRegion):
            pass

        def add_player(self, user_id: int):
            pass

        def get_players(self):
            pass

        def get_player(self, user_id: int):
            pass

        def remove_player(self, player):
            pass

        def fresh_creature_id(self):
            pass

        def add_creature(self, creature: BaseCreature, owner):
            pass

        def get_creatures(self):
            pass

        def get_creature(self, creature_id: int):
            pass

        def remove_creature(self, creature):
            pass

        def add_to_creature_pool(self, creature: BaseCreature):
            pass

        def get_creature_pool(self):
            pass

        def get_random_from_creature_pool(self):
            pass

        def remove_from_creature_pool(self, creature: BaseCreature):
            pass

        def add_free_creature(
            self, creature: BaseCreature, channel_id: int, message_id: int, roller
        ):
            pass

        def get_free_creatures(self):
            pass

        def get_free_creature(self, channel_id: int, message_id: int):
            pass

        def remove_free_creature(self, creature):
            pass

    class Region:

        def __init__(self, id: int, parent, region: BaseRegion, guild):
            self.id = id
            self.parent = parent
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

        def occupy(self, creature):
            pass

        def unoccupy(self, current: int):
            pass

        def occupied(self) -> tuple:
            pass

        class RegionRechargeEvent(Event):

            def __init__(self, id: int, parent, guild, timestamp: int, region):
                super().__init__(id, parent, timestamp, guild)
                self.region = region

            def resolve(self):
                self.region.unoccupy(self.timestamp)

    class Player:

        def __init__(self, parent, guild, user_id: int):
            self.parent = parent
            self.guild = guild
            self.id = user_id

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

        def get_resources(self) -> dict[Resource, int]:
            pass

        def set_resources(self, resources: dict[Resource, int]):
            pass

        def get_deck(self):
            pass

        def get_hand(self):
            pass

        def get_played(self):
            pass

        def get_discard(self):
            pass

        def get_full_deck(self):
            return sorted(
                self.get_deck() + self.get_hand() + self.get_played() + self.get_discard(),
                key=lambda x: str(x),
            )

        def has(self, resource: Resource, amount: int, in_trans=False) -> bool:
            return self.fulfills_price([Price(resource, amount)])

        def give(self, resource: Resource, amount: int) -> None:
            self.gain([Gain(resource, amount)])

        def remove(self, resource: Resource, amount: int) -> None:
            self.give(resource, -amount)

        def fulfills_price(self, price: list[Price], in_trans=False) -> bool:
            merged_prices = defaultdict(lambda: 0)
            for p in price:
                if p.amount == 0:
                    continue

                merged_prices[p.resource] += p.amount

            if len(merged_prices) == 0:
                return True

            resources: dict[Resource, int] = self.get_resources()
            hand_size: list = len(self.get_hand())

            for r, a in merged_prices.items():
                if r in BaseResources:
                    if resources[r] < a:
                        return False
                elif r == Resource.DELETE_CREATURES:
                    if hand_size < a:
                        return False
            return True

        def _delete_creatures(self, hand_size: int, a: int, extra_data: dict):
            if hand_size < a:
                raise NoCreaturesToDeleteProvided(
                    "Need to delete {} creatures, only have {} creatures in hand".format(
                        a, hand_size
                    )
                )

            try:
                creatures_to_delete = extra_data["creatures_to_delete"]
            except KeyError:
                raise NoCreaturesToDeleteProvided()

            if len(creatures_to_delete) < a:
                raise NoCreaturesToDeleteProvided(
                    "Expected at least {} creatures to delete, only got {}".format(
                        a, len(creatures_to_delete)
                    )
                )

            # like this extra_data can be further propagated
            extra_data["creatures_to_delete"] -= a

            creatures_to_delete = creatures_to_delete[:a]
            for c in creatures_to_delete:
                self.delete_creature_from_hand(c)

        def gain(self, gain: list[Gain], in_trans=False, extra_data={}) -> None:
            merged_gains = defaultdict(lambda: 0)
            for g in gain:
                if g.amount == 0:
                    continue
                merged_gains[g.resource] += g.amount

            if len(merged_gains) == 0:
                return

            with self.parent.Transaction(self.parent, in_trans):

                resources: dict[Resource, int] = self.get_resources()
                hand_size: list = len(self.get_hand())

                for r, a in merged_gains.items():
                    if r in BaseResources:
                        resources[r] += a
                    elif r == Resource.CREATURES_IN_HAND:
                        self.draw_cards(N=a, in_trans=True)
                    elif r == Resource.DELETE_CREATURES:
                        self._delete_creatures(hand_size, a, extra_data)

                self.set_resources(resources)

        def pay_price(self, price: list[Price], in_trans=False, extra_data={}) -> None:
            merged_price = defaultdict(lambda: 0)
            for p in price:
                if p.amount == 0:
                    continue
                merged_price[p.resource] += p.amount

            if len(merged_price) == 0:
                return

            with self.parent.Transaction(self.parent, in_trans):

                resources: dict[Resource, int] = self.get_resources()
                hand_size: list = len(self.get_hand())

                for r, a in merged_price.items():
                    if r in BaseResources:
                        if resources[r] < a:
                            raise NotEnoughResourcesException(
                                "Player is paying {} {} but only has {}".format(a, r, resources[r])
                            )
                        resources[r] -= a
                    elif r == Resource.DELETE_CREATURES:
                        self._delete_creatures(hand_size, a, extra_data)
                self.set_resources(resources)

        def draw_card_raw(self) -> BaseCreature:
            pass

        def reshuffle_discard(self) -> None:
            pass

        def draw_cards(self, N=1, in_trans=False) -> tuple[int, bool]:
            with self.parent.Transaction(self.parent, in_trans):
                cards_drawn = []
                discard_reshuffled = False
                for _ in range(N):
                    if len(self.get_deck()) == 0:
                        self.reshuffle_discard()
                        discard_reshuffled = True

                        if len(self.get_deck()) == 0:
                            return cards_drawn, discard_reshuffled

                    card = self.draw_card_raw()
                    cards_drawn.append(card)

                return cards_drawn, discard_reshuffled

        def delete_creature_from_hand(self, creature) -> None:
            pass

        def play_creature(self, creature) -> None:
            pass

        def add_to_discard(self, creature) -> None:
            pass

        def play_creature_to_region(self, creature, region, in_trans=False, extra_data={}):

            if region.region.category not in creature.creature.quest_region_categories:
                raise CreatureCannotQuestHere(
                    f"Region is {region.region.category} but creature can only go to {creature.creature.quest_region_categories}"
                )

            price, gain = region.region.quest_effect()
            creature_price, creature_gain = creature.creature.quest_ability_effect()

            with self.parent.Transaction(self.parent, in_trans):
                self.pay_price([Price(Resource.ORDERS, 1)], in_trans=True)
                self.pay_price(price, in_trans=True, extra_data=extra_data)
                if len(creature_price) > 0 and "pay_creature_price" in extra_data:
                    self.pay_price(creature_price, in_trans=True, extra_data=extra_data)
                self.play_creature(creature)
                region: Database.Region = region
                region.occupy(creature)
                creature.play()
                self.gain(gain, in_trans=True, extra_data=extra_data)
                if len(creature_price) == 0 or (
                    len(creature_price) > 0 and "pay_creature_price" in extra_data
                ):
                    self.gain(creature_gain, in_trans=True, extra_data=extra_data)

        def play_creature_to_campaign(self, creature, in_trans=False, extra_data={}):

            creature_price, creature_gain = creature.creature.campaign_ability_effect()

            with self.parent.Transaction(self.parent, in_trans):
                if len(creature_price) > 0 and "pay_creature_price" in extra_data:
                    self.pay_price(creature_price, in_trans=True, extra_data=extra_data)
                self.play_creature(creature)
                if len(creature_price) == 0 or (
                    len(creature_price) > 0 and "pay_creature_price" in extra_data
                ):
                    self.gain(creature_gain, in_trans=True, extra_data=extra_data)

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

        def play(self):
            pass

        class CreatureRechargeEvent(Event):

            def __init__(self, id: int, parent, guild, timestamp: int, creature):
                super().__init__(id, parent, timestamp, guild)
                self.creature = creature

            def resolve(self):
                self.creature.owner.add_to_discard(self.creature)

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

        def get_protected_timestamp(self) -> int:
            pass

        def get_expires_timestamp(self) -> int:
            pass

        def is_protected(self, timestamp: int) -> bool:
            return self.get_protected_timestamp() > timestamp

        def is_expired(self, timestamp: int) -> bool:
            return self.get_expires_timestamp() < timestamp

        def claimed(self):
            pass

        def claim(self, timestamp: int, owner, in_trans=False):

            owner: Database.Player = owner
            guild: Database.Guild = self.guild

            guild.get_free_creature(self.channel_id, self.message_id)

            if self.is_expired(timestamp):
                raise ExpiredFreeCreature()

            if self.is_protected(timestamp) and owner != self.roller:
                raise ProtectedFreeCreature(
                    f"This creature is protected until {self.get_protected_timestamp()}"
                )

            with self.parent.Transaction(self.parent, in_trans):
                owner.pay_price([Price(Resource.RALLY, self.creature.claim_cost)], in_trans=True)
                guild.remove_free_creature(self)
                guild.add_creature(self.creature, owner)
                self.claimed()

        class FreeCreatureProtectedEvent(Event):

            def __init__(self, id: int, parent, guild, timestamp: int, free_creature):
                super().__init__(id, parent, timestamp, guild)
                self.free_creature = free_creature

        class FreeCreatureExpiresEvent(Event):

            def __init__(self, id: int, parent, guild, timestamp: int, free_creature):
                super().__init__(id, parent, timestamp, guild)
                self.free_creature = free_creature

            def resolve(self):
                self.guild.remove_free_creature(self.free_creature)
