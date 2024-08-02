import time
import json
import copy
from typing import List, Tuple
from collections import defaultdict

from src.core.base_types import (
    Resource,
    Price,
    Gain,
    BaseResources,
    BaseCreature,
    BaseRegion,
    Event,
    StartCondition,
    resource_changes_to_string,
    resource_changes_to_short_string,
)
from src.core.exceptions import (
    MissingExtraData,
    BadExtraData,
    NotEnoughResourcesException,
    CreatureCannotQuestHere,
    ExpiredFreeCreature,
    ProtectedFreeCreature,
    CreatureNotFound,
)


class Database:

    def __init__(self, start_condition: StartCondition):
        self.start_condition = start_condition

    def timestamp_after(self, seconds: int):
        return int(time.time() + seconds)

    class TransactionManager:

        def __init__(self, parent, parent_manager):
            self.parent: Database = parent
            self.parent_manager: Database.TransactionManager = parent_manager
            self.children: list[Database.TransactionManager] = []
            self.events: list[Event] = []

            self.con = None
            self.trans = None

        def __enter__(self):
            if self.parent_manager is None:
                con, trans = self.start_connection()
            else:
                con = self.parent_manager.con
                trans = self.parent_manager.trans
                self.parent_manager.children.append(self)

            self.con = con
            self.trans = trans

            return self

        def __exit__(self, exc_type, exc_value, traceback):
            if self.parent_manager is None:
                if exc_type is not None:
                    self.rollback_transaction()
                    return False

                for e in self.get_events():
                    self.parent.add_event(e, con=self)

                self.commit_transaction()
                self.end_connection()
                return True
            else:
                if exc_type is not None:
                    return False
                return True

        def start_connection(self):
            pass

        def end_connection(self):
            pass

        def commit_transaction(self):
            pass

        def rollback_transaction(self):
            pass

        def execute(self, *args):
            pass

        def add_event(self, event: Event):
            if self.parent_manager:
                parent = self.parent_manager
                while parent.events == [] and parent.parent_manager:
                    parent = parent.parent_manager

                if parent.events != [] and event.parent_event is None:
                    event.parent_event = parent.events[-1]
            self.events.append(event)

        def get_events(self):
            return self.events + sum([c.get_events() for c in self.children], [])

        def get_root(self):
            if self.parent_manager is None:
                return self
            return self.parent_manager.get_root()

    def transaction(self, parent: TransactionManager = None):
        return self.TransactionManager(self, parent)

    def fresh_event_id(self, guild, con=None):
        pass

    def add_event(self, event: Event, con=None):
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

        def get_events(
            self, timestamp_start: int, timestamp_end: int, event_type=None, con=None
        ) -> list[Event]:
            pass

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

        def get_region(self, region_id: int, con=None):
            pass

        def remove_region(self, region, con=None):
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

        class RegionAddedEvent(Event):

            event_type = "region_added"

            def __init__(
                self, parent, id: int, timestamp: int, parent_event: Event, guild, region_id: int
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.region_id = region_id

            def from_extra_data(
                parent, id: int, timestamp: int, parent_event, guild, extra_data: dict
            ):
                return Database.Guild.RegionAddedEvent(
                    parent, id, timestamp, parent_event, guild, extra_data["region_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"region_id": self.region_id})

            def text(self) -> str:
                return f"<region:{self.region_id}> has been added"

        class RegionRemovedEvent(Event):

            event_type = "region_removed"

            def __init__(
                self, parent, id: int, timestamp: int, parent_event: Event, guild, region_id: int
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.region_id = region_id

            def from_extra_data(
                parent, id: int, timestamp: int, parent_event, guild, extra_data: dict
            ):
                return Database.Guild.RegionEvent(
                    parent, id, timestamp, parent_event, guild, extra_data["region_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"region_id": self.region_id})

            def text(self) -> str:
                return f"<region:{self.region_id}> has been remvoed"

        class PlayerAddedEvent(Event):

            event_type = "player_added"

            def __init__(
                self, parent, id: int, timestamp: int, parent_event: Event, guild, player_id: int
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id

            def from_extra_data(
                parent, id: int, timestamp: int, parent_event, guild, extra_data: dict
            ):
                return Database.Guild.PlayerAddedEvent(
                    parent, id, timestamp, parent_event, guild, extra_data["player_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"player_id": self.player_id})

            def text(self) -> str:
                return f"<player:{self.player_id}> has joined"

        class PlayerRemovedEvent(Event):

            event_type = "player_removed"

            def __init__(
                self, parent, id: int, timestamp: int, parent_event: Event, guild, player_id: int
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id

            def from_extra_data(
                parent, id: int, timestamp: int, parent_event, guild, extra_data: dict
            ):
                return Database.Guild.PlayerRemovedEvent(
                    parent, id, timestamp, parent_event, guild, extra_data["player_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"player_id": self.player_id})

            def text(self) -> str:
                return f"<player:{self.player_id}> has left"

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

            event_type = "region_recharge"

            def __init__(
                self, parent, id: int, timestamp: int, parent_event: Event, guild, region_id: int
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.region_id = region_id

            def from_extra_data(
                parent, id: int, timestamp: int, parent_event, guild, extra_data: dict
            ):
                return Database.Region.RegionRechargeEvent(
                    parent, id, timestamp, parent_event, guild, extra_data["region_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"region_id": self.region_id})

            def text(self) -> str:
                return f"{self.region_id} has recharged"

            def resolve(self, con=None):
                self.guild.get_region(self.region_id).unoccupy(self.timestamp, con=con)

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

        def get_played(self, con=None):
            pass

        def get_full_deck(self, con=None):
            with self.parent.transaction(parent=con) as con:
                return sorted(
                    self.get_deck(con=con)
                    + self.get_hand(con=con)
                    + self.get_discard(con=None)
                    + self.get_played(con=None),
                    key=lambda x: str(x),
                )

        def get_campaign(self, con=None):
            pass

        def get_events(
            self, timestamp_start: int, timestamp_end: int, event_type=None, con=None
        ) -> list[Event]:
            pass

        def remove_event(self, event: Event, con=None) -> Event:
            pass

        def get_recharges(self, con=None) -> dict:
            recharge_event_classes: list[type[Event]] = [
                Database.Player.PlayerOrderRechargeEvent,
                Database.Player.PlayerMagicRechargeEvent,
                Database.Player.PlayerCardRechargeEvent,
            ]

            r = {}

            for c in recharge_event_classes:
                events = self.get_events(0, time.time() * 2, event_type=c.event_type)
                assert len(events) == 1
                recharge_event = events[0]
                r[c.event_type] = recharge_event

            return r

        def has(self, resource: Resource, amount: int, con=None) -> bool:
            return self.fulfills_price([Price(resource, amount)], con=con)

        def give(self, resource: Resource, amount: int, con=None) -> None:
            self.gain([Gain(resource, amount)], con=con)

        def remove(self, resource: Resource, amount: int, con=None) -> None:
            self.pay_price([Price(resource, amount)], con=con)

        def fulfills_price(self, price: list[Price], con=None) -> bool:
            merged_prices = defaultdict(lambda: 0)
            for p in price:
                if p.amount == 0:
                    continue

                merged_prices[p.resource] += p.amount

            if len(merged_prices) == 0:
                return True

            with self.parent.transaction(parent=con) as con:
                resources: dict[Resource, int] = self.get_resources(con=con)
                hand_size: list = len(self.get_hand(con=con))

            for r, a in merged_prices.items():
                if r in BaseResources:
                    if resources[r] < a:
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

            with self.parent.transaction(parent=con) as con:
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

            with self.parent.transaction(parent=con) as con:
                event_id = self.parent.fresh_event_id(self.guild, con=con)
                con.add_event(
                    Database.Player.PlayerGainEvent(
                        self.parent,
                        event_id,
                        time.time(),
                        None,
                        self.guild,
                        self.id,
                        [(g.resource.value, g.amount) for g in gain],
                    ),
                )

                resources: dict[Resource, int] = self.get_resources(con=con)
                hand_size: list = len(self.get_hand(con=con))

                for r, a in merged_gains.items():
                    if r in BaseResources:
                        resources[r] += a

                self.set_resources(resources, con=con)

        def pay_price(self, price: list[Price], con=None, extra_data={}) -> None:
            merged_price = defaultdict(lambda: 0)
            for p in price:
                if p.amount == 0:
                    continue
                merged_price[p.resource] += p.amount

            if len(merged_price) == 0:
                return

            with self.parent.transaction(parent=con) as con:
                event_id = self.parent.fresh_event_id(self.guild, con=con)
                con.add_event(
                    Database.Player.PlayerPayEvent(
                        self.parent,
                        event_id,
                        time.time(),
                        None,
                        self.guild,
                        self.id,
                        [(p.resource.value, p.amount) for p in price],
                    ),
                )

                resources: dict[Resource, int] = self.get_resources(con=con)
                hand_size: list = len(self.get_hand(con=con))

                for r, a in merged_price.items():
                    if r in BaseResources:
                        if resources[r] < a:
                            raise NotEnoughResourcesException(
                                "Player is paying {} {} but only has {}".format(a, r, resources[r])
                            )
                        resources[r] -= a
                self.set_resources(resources, con=con)

        def draw_card_raw(self, con=None) -> BaseCreature:
            pass

        def reshuffle_discard(self, con=None) -> None:
            pass

        def draw_cards(self, N=1, con=None) -> tuple[int, bool]:
            with self.parent.transaction(parent=con) as con:
                max_cards = self.guild.get_config(con=con)["max_cards"]
                current_cards = len(self.get_hand(con=con))

                cards_drawn = []
                discard_reshuffled = False
                hand_full = False
                for _ in range(N):
                    assert current_cards + len(cards_drawn) <= max_cards

                    if current_cards + len(cards_drawn) == max_cards:
                        hand_full = True
                        break

                    if len(self.get_deck(con=con)) == 0:
                        self.reshuffle_discard(con=con)
                        discard_reshuffled = True

                        if len(self.get_deck(con=con)) == 0:
                            break

                    card = self.draw_card_raw(con=con)
                    cards_drawn.append(card)

                event_id = self.parent.fresh_event_id(self.guild, con=con)
                con.add_event(
                    Database.Player.PlayerDrawEvent(
                        self.parent,
                        event_id,
                        time.time(),
                        None,
                        self.guild,
                        self.id,
                        len(cards_drawn),
                    ),
                )

                return cards_drawn, discard_reshuffled, hand_full

        def delete_creature_from_hand(self, creature, con=None) -> None:
            pass

        def recharge_creature(self, creature, con=None):
            pass

        def play_creature(self, creature, con=None) -> None:
            pass

        def campaign_creature(self, creature, strength: int, con=None) -> None:
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

            with self.parent.transaction(parent=con) as con:
                event_id = self.parent.fresh_event_id(self.guild, con=con)
                con.add_event(
                    Database.Player.PlayerPlayToRegionEvent(
                        self.parent,
                        event_id,
                        time.time(),
                        None,
                        self.guild,
                        self.id,
                        creature.id,
                        region.id,
                        copy.deepcopy(extra_data),
                    )
                )

                self.pay_price([Price(Resource.ORDERS, 1)], con=con)
                base_creature.quest_ability_effect_price(
                    region, creature, con=con, extra_data=extra_data
                )
                base_region.quest_effect_price(region, creature, con=con, extra_data=extra_data)
                self.play_creature(creature, con=con)
                region: Database.Region = region
                region.occupy(creature, con=con)
                creature: Database.Creature = creature
                creature.play(con=con)
                base_region.quest_effect(region, creature, con=con, extra_data=extra_data)
                base_creature.quest_ability_effect(region, creature, con=con, extra_data=extra_data)

        def play_creature_to_campaign(self, creature, con=None, extra_data={}):

            base_creature: BaseCreature = creature.creature

            with self.parent.transaction(parent=con) as con:
                event_id = self.parent.fresh_event_id(self.guild, con=con)
                con.add_event(
                    Database.Player.PlayerPlayToCampaignEvent(
                        self.parent,
                        event_id,
                        time.time(),
                        None,
                        self.guild,
                        self.id,
                        creature.id,
                        copy.deepcopy(extra_data),
                    )
                )

                base_creature.campaign_ability_effect_price(
                    creature, con=con, extra_data=extra_data
                )
                strength = base_creature.campaign_ability_effect(
                    creature, con=con, extra_data=extra_data
                )
                self.campaign_creature(creature, strength, con=con)

        class PlayerDrawEvent(Event):

            event_type = "player_draw"

            def __init__(
                self,
                parent,
                id: int,
                timestamp: int,
                parent_event: Event,
                guild,
                player_id: int,
                num_cards: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id
                self.num_cards = num_cards

            def from_extra_data(
                parent, id: int, timestamp: int, parent_event, guild, extra_data: dict
            ):
                return Database.Player.PlayerDrawEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event,
                    guild,
                    extra_data["player_id"],
                    extra_data["num_cards"],
                )

            def extra_data(self) -> str:
                return json.dumps({"player_id": self.player_id, "num_cards": self.num_cards})

            def text(self) -> str:
                return f"<player:{self.player_id}> draws {self.num_cards} cards"

        class PlayerGainEvent(Event):

            event_type = "player_gain"

            def __init__(
                self,
                parent,
                id: int,
                timestamp: int,
                parent_event: Event,
                guild,
                player_id: int,
                changes: List[Tuple[int, int]],
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id
                self.changes = changes

            def from_extra_data(
                parent, id: int, timestamp: int, parent_event, guild, extra_data: dict
            ):
                return Database.Player.PlayerGainEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event,
                    guild,
                    extra_data["player_id"],
                    list(map(tuple, extra_data["changes"])),
                )

            def extra_data(self) -> str:
                return json.dumps({"player_id": self.player_id, "changes": self.changes})

            def text(self) -> str:
                gain_list = list(
                    map(lambda x: Gain(resource=Resource(x[0]), amount=x[1]), self.changes)
                )
                gain_string = resource_changes_to_string(gain_list, third_person=True)
                return f"<player:{self.player_id}> {gain_string}"

        class PlayerPayEvent(Event):

            event_type = "player_pay"

            def __init__(
                self,
                parent,
                id: int,
                timestamp: int,
                parent_event: Event,
                guild,
                player_id: int,
                changes: List[Tuple[int, int]],
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id
                self.changes = changes

            def from_extra_data(
                parent, id: int, timestamp: int, parent_event, guild, extra_data: dict
            ):
                return Database.Player.PlayerPayEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event,
                    guild,
                    extra_data["player_id"],
                    list(map(tuple, extra_data["changes"])),
                )

            def extra_data(self) -> str:
                return json.dumps({"player_id": self.player_id, "changes": self.changes})

            def text(self) -> str:
                gain_list = list(
                    map(lambda x: Price(resource=Resource(x[0]), amount=x[1]), self.changes)
                )
                gain_string = resource_changes_to_string(gain_list, third_person=True)
                return f"<player:{self.player_id}> {gain_string}"

        class PlayerPlayToRegionEvent(Event):

            event_type = "player_play_to_region"

            def __init__(
                self,
                parent,
                id: int,
                timestamp: int,
                parent_event: Event,
                guild,
                player_id: int,
                creature_id: int,
                region_id: int,
                play_extra_data: dict,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id
                self.creature_id = creature_id
                self.region_id = region_id
                self.play_extra_data = play_extra_data

            def from_extra_data(
                parent, id: int, timestamp: int, parent_event, guild, extra_data: dict
            ):
                return Database.Player.PlayerPlayToRegionEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event,
                    guild,
                    extra_data["player_id"],
                    extra_data["creature_id"],
                    extra_data["region_id"],
                    extra_data["play_extra_data"],
                )

            def extra_data(self) -> str:
                return json.dumps(
                    {
                        "player_id": self.player_id,
                        "creature_id": self.creature_id,
                        "region_id": self.region_id,
                        "play_extra_data": self.play_extra_data,
                    }
                )

            def text(self) -> str:
                return f"<player:{self.player_id}> sends <creature:{self.creature_id}> to <region:{self.region_id}>"

        class PlayerPlayToCampaignEvent(Event):

            event_type = "player_play_to_campaign"

            def __init__(
                self,
                parent,
                id: int,
                timestamp: int,
                parent_event: Event,
                guild,
                player_id: int,
                creature_id: int,
                play_extra_data: dict,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id
                self.creature_id = creature_id
                self.play_extra_data = play_extra_data

            def from_extra_data(
                parent, id: int, timestamp: int, parent_event, guild, extra_data: dict
            ):
                return Database.Player.PlayerPlayToCampaignEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event,
                    guild,
                    extra_data["player_id"],
                    extra_data["creature_id"],
                    extra_data["play_extra_data"],
                )

            def extra_data(self) -> str:
                return json.dumps(
                    {
                        "player_id": self.player_id,
                        "creature_id": self.creature_id,
                        "play_extra_data": self.play_extra_data,
                    }
                )

            def text(self) -> str:
                return f"<player:{self.player_id}> makes <creature:{self.creature_id}> campaign"

        class PlayerOrderRechargeEvent(Event):

            event_type = "player_order_recharge"

            def __init__(
                self,
                parent,
                id: int,
                timestamp: int,
                parent_event: Event,
                guild,
                player_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id

            def from_extra_data(
                parent, id: int, timestamp: int, parent_event, guild, extra_data: dict
            ):
                return Database.Player.PlayerOrderRechargeEvent(
                    parent, id, timestamp, parent_event, guild, extra_data["player_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"player_id": self.player_id})

            def text(self) -> str:
                return f"<player:{self.player_id}> recharges on orders"

            def resolve(self, con=None):
                with self.parent.transaction(parent=con) as con:
                    player: Database.Player = self.guild.get_player(self.player_id, con=con)
                    guild_config = self.guild.get_config(con=con)
                    player_orders = player.get_resources(con=con)[Resource.ORDERS]
                    if player_orders + 1 <= guild_config["max_orders"]:
                        player.gain([Gain(resource=Resource.ORDERS, amount=1)], con=con)

                    event_id = self.parent.fresh_event_id(self.guild, con=con)
                    con.add_event(
                        Database.Player.PlayerOrderRechargeEvent(
                            self.parent,
                            event_id,
                            time.time() + guild_config["order_recharge"],
                            None,
                            self.guild,
                            self.player_id,
                        ),
                    )

        class PlayerMagicRechargeEvent(Event):

            event_type = "player_magic_recharge"

            def __init__(
                self,
                parent,
                id: int,
                timestamp: int,
                parent_event: Event,
                guild,
                player_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id

            def from_extra_data(
                parent, id: int, timestamp: int, parent_event, guild, extra_data: dict
            ):
                return Database.Player.PlayerMagicRechargeEvent(
                    parent, id, timestamp, parent_event, guild, extra_data["player_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"player_id": self.player_id})

            def text(self) -> str:
                return f"<player:{self.player_id}> recharges on magic"

            def resolve(self, con=None):
                with self.parent.transaction(parent=con) as con:
                    player: Database.Player = self.guild.get_player(self.player_id, con=con)
                    guild_config = self.guild.get_config(con=con)
                    player_magic = player.get_resources(con=con)[Resource.MAGIC]
                    if player_magic + 1 <= guild_config["max_magic"]:
                        player.gain([Gain(resource=Resource.MAGIC, amount=1)], con=con)

                    event_id = self.parent.fresh_event_id(self.guild, con=con)
                    con.add_event(
                        Database.Player.PlayerMagicRechargeEvent(
                            self.parent,
                            event_id,
                            time.time() + guild_config["magic_recharge"],
                            None,
                            self.guild,
                            self.player_id,
                        ),
                    )

        class PlayerCardRechargeEvent(Event):

            event_type = "player_card_recharge"

            def __init__(
                self,
                parent,
                id: int,
                timestamp: int,
                parent_event: Event,
                guild,
                player_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id

            def from_extra_data(
                parent, id: int, timestamp: int, parent_event, guild, extra_data: dict
            ):
                return Database.Player.PlayerCardRechargeEvent(
                    parent, id, timestamp, parent_event, guild, extra_data["player_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"player_id": self.player_id})

            def text(self) -> str:
                return f"<player:{self.player_id}> recharges on cards"

            def resolve(self, con=None):
                with self.parent.transaction(parent=con) as con:
                    player: Database.Player = self.guild.get_player(self.player_id, con=con)
                    guild_config = self.guild.get_config(con=con)
                    player.draw_cards(1, con=con)

                    event_id = self.parent.fresh_event_id(self.guild, con=con)
                    con.add_event(
                        Database.Player.PlayerCardRechargeEvent(
                            self.parent,
                            event_id,
                            time.time() + guild_config["card_recharge"],
                            None,
                            self.guild,
                            self.player_id,
                        ),
                    )

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

        def play(self, parent_event=None, con=None):
            with self.parent.transaction(parent=con) as con:
                until = self.parent.timestamp_after(self.guild.get_config()["creature_recharge"])

                event_id = self.parent.fresh_event_id(self.guild, con=con)
                # add directly to parent instead of connection
                self.parent.add_event(
                    Database.Creature.CreatureRechargeEvent(
                        self.parent,
                        event_id,
                        until,
                        None,
                        self.guild,
                        self.id,
                    )
                )

        class CreatureRechargeEvent(Event):

            event_type = "creature_recharge"

            def __init__(
                self, parent, id: int, timestamp: int, parent_event: Event, guild, creature_id: int
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.creature_id = creature_id

            def from_extra_data(
                parent, id: int, timestamp: int, parent_event, guild, extra_data: dict
            ):
                return Database.Creature.CreatureRechargeEvent(
                    parent, id, timestamp, parent_event, guild, extra_data["creature_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"creature_id": self.creature_id})

            def text(self) -> str:
                return "{creature_id} has recharged"

            def resolve(self, con=None):
                with self.parent.transaction(parent=con) as con:
                    creature = self.guild.get_creature(self.creature_id)
                    creature.owner.recharge_creature(creature)

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

        def create_events(self, con=None):
            with self.parent.transaction(parent=con) as con:
                # Notice that we add the events to the parent directly instead of the connection
                # that is because we do not want these events to be part of the transaction
                event_id = self.parent.fresh_event_id(self.guild, con=con)
                self.parent.add_event(
                    Database.FreeCreature.FreeCreatureProtectedEvent(
                        self.parent,
                        event_id,
                        self.get_protected_timestamp(con=con),
                        None,
                        self.guild,
                        self.channel_id,
                        self.message_id,
                    )
                )

                event_id = self.parent.fresh_event_id(self.guild, con=con)
                self.parent.add_event(
                    Database.FreeCreature.FreeCreatureExpiresEvent(
                        self.parent,
                        event_id,
                        self.get_expires_timestamp(con=con),
                        None,
                        self.guild,
                        self.channel_id,
                        self.message_id,
                    )
                )

        def get_protected_timestamp(self, con=None) -> int:
            pass

        def get_expires_timestamp(self, con=None) -> int:
            pass

        def is_protected(self, timestamp: int, con=None) -> bool:
            return self.get_protected_timestamp(con=con) > timestamp

        def is_expired(self, timestamp: int, con=None) -> bool:
            return self.get_expires_timestamp(con=con) < timestamp

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

            with self.parent.transaction(parent=con) as con:
                owner.pay_price([Price(Resource.RALLY, self.creature.claim_cost)], con=con)
                # dont do this for now so that information about claimed creatures can still be queried
                # guild.remove_free_creature(self, con=con)
                creature: Database.Creature = guild.add_creature(self.creature, owner, con=con)
                owner.add_to_discard(creature, con=con)

                event_id = self.parent.fresh_event_id(self.guild, con=con)
                con.add_event(
                    Database.FreeCreature.FreeCreatureClaimedEvent(
                        self.parent,
                        event_id,
                        time.time(),
                        None,
                        self.guild,
                        self.channel_id,
                        self.message_id,
                        owner.id,
                        creature.id,
                    )
                )

        class FreeCreatureProtectedEvent(Event):

            event_type = "free_creature_protected"

            def __init__(
                self,
                parent,
                id: int,
                timestamp: int,
                parent_event: Event,
                guild,
                channel_id: int,
                message_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.channel_id = channel_id
                self.message_id = message_id

            def from_extra_data(
                parent, id: int, timestamp: int, parent_event, guild, extra_data: dict
            ):
                return Database.FreeCreature.FreeCreatureProtectedEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event,
                    guild,
                    extra_data["channel_id"],
                    extra_data["message_id"],
                )

            def extra_data(self) -> str:
                return json.dumps({"channel_id": self.channel_id, "message_id": self.message_id})

            def text(self) -> str:
                return (
                    f"<free_creature:({self.channel_id},{self.message_id})> is no longer protected"
                )

        class FreeCreatureExpiresEvent(Event):

            event_type = "free_creature_expires"

            def __init__(
                self,
                parent,
                id: int,
                timestamp: int,
                parent_event: Event,
                guild,
                channel_id: int,
                message_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.channel_id = channel_id
                self.message_id = message_id

            def from_extra_data(
                parent, id: int, timestamp: int, parent_event, guild, extra_data: dict
            ):
                return Database.FreeCreature.FreeCreatureExpiresEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event,
                    guild,
                    extra_data["channel_id"],
                    extra_data["message_id"],
                )

            def extra_data(self) -> str:
                return json.dumps({"channel_id": self.channel_id, "message_id": self.message_id})

            def text(self) -> str:
                return f"<free_creature:({self.channel_id},{self.message_id})> has expired"

            def resolve(self, con=None):
                with self.parent.transaction(parent=con) as con:
                    try:
                        free_creature: Database.FreeCreature = self.guild.get_free_creature(
                            self.channel_id, self.message_id, con=con
                        )
                        self.guild.remove_free_creature(free_creature, con=con)
                    except CreatureNotFound:
                        pass

        class FreeCreatureClaimedEvent(Event):

            event_type = "free_creature_claimed"

            def __init__(
                self,
                parent,
                id: int,
                timestamp: int,
                parent_event: Event,
                guild,
                channel_id: int,
                message_id: int,
                player_id: int,
                creature_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.channel_id = channel_id
                self.message_id = message_id
                self.player_id = player_id
                self.creature_id = creature_id

            def from_extra_data(
                parent, id: int, timestamp: int, parent_event, guild, extra_data: dict
            ):
                return Database.FreeCreature.FreeCreatureClaimedEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event,
                    guild,
                    extra_data["channel_id"],
                    extra_data["message_id"],
                    extra_data["player_id"],
                    extra_data["creature_id"],
                )

            def extra_data(self) -> str:
                return json.dumps(
                    {
                        "channel_id": self.channel_id,
                        "message_id": self.message_id,
                        "player_id": self.player_id,
                        "creature_id": self.creature_id,
                    }
                )

            def text(self) -> str:
                return f"<free_creature:({self.channel_id},{self.message_id})> has been claimed by <player:{self.player_id}>: <creature:{self.creature_id}>"


event_classes: list[type[Event]] = [
    Database.Guild.RegionAddedEvent,
    Database.Guild.RegionRemovedEvent,
    Database.Guild.PlayerAddedEvent,
    Database.Guild.PlayerRemovedEvent,
    Database.Region.RegionRechargeEvent,
    Database.Creature.CreatureRechargeEvent,
    Database.FreeCreature.FreeCreatureProtectedEvent,
    Database.FreeCreature.FreeCreatureExpiresEvent,
    Database.Player.PlayerDrawEvent,
    Database.Player.PlayerGainEvent,
    Database.Player.PlayerPayEvent,
    Database.Player.PlayerPlayToRegionEvent,
    Database.Player.PlayerPlayToCampaignEvent,
    Database.FreeCreature.FreeCreatureClaimedEvent,
    Database.Player.PlayerOrderRechargeEvent,
    Database.Player.PlayerMagicRechargeEvent,
    Database.Player.PlayerCardRechargeEvent,
]
