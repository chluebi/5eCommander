from __future__ import annotations

import time
import json
import copy
from typing import List, Tuple, Type, Optional, Union, Any, cast, Generic, TypeVar
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
    RegionCategory,
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


from sqlalchemy import (
    RootTransaction,
    Connection
)


class Database:

    def __init__(self, start_condition: StartCondition):
        self.start_condition = start_condition

    def timestamp_after(self, seconds: float) -> float:
        return float(time.time() + seconds)

    class TransactionManager:

        def __init__(
            self,
            parent: Database,
            parent_manager: Optional[Database.TransactionManager],
        ):
            self.parent: Database = parent
            self.parent_manager = parent_manager
            self.children: list[Database.TransactionManager] = []
            self.events: list[Event] = []

            self.con: Connection = cast(Connection, None)
            self.trans: RootTransaction = cast(RootTransaction, None)

        def __enter__(self) -> Database.TransactionManager:
            if self.parent_manager is None:
                res = self.start_connection()
                self.con = res[0]
                self.trans = res[1]
            else:
                assert self.parent_manager.con is not None
                assert self.parent_manager.trans is not None
                self.con = self.parent_manager.con
                self.trans = self.parent_manager.trans
                self.parent_manager.children.append(self)


            return self

        def __exit__(
            self,
            exc_type: Optional[Type[Exception]],
            exc_value: Optional[Exception],
            traceback: Any,
        ) -> None:
            if self.parent_manager is None:
                if exc_value is not None:
                    self.rollback_transaction()
                    raise exc_value

                for e in self.get_events():
                    self.parent.add_event(e, con=self)

                self.commit_transaction()
                self.end_connection()
            else:
                if exc_value is not None:
                    raise exc_value

        def start_connection(self) -> Tuple[Connection, RootTransaction]:
            assert False

        def end_connection(self) -> None:
            assert False

        def commit_transaction(self) -> None:
            assert False

        def rollback_transaction(self) -> None:
            assert False

        def execute(self, *args: Any) -> Any:
            assert False

        def add_event(self, event: Event) -> None:
            if self.parent_manager:
                parent = self.parent_manager
                while parent.events == [] and parent.parent_manager:
                    parent = parent.parent_manager

                if parent.events != [] and event.parent_event is None:
                    event.parent_event = parent.events[-1]
            self.events.append(event)

        def get_events(self) -> List[Event]:
            return self.events + sum([c.get_events() for c in self.children], [])

        def get_root(self) -> Database.TransactionManager:
            if self.parent_manager is None:
                return self
            return self.parent_manager.get_root()

    def transaction(
        self, parent: Optional[Database.TransactionManager] = None
    ) -> TransactionManager:
        return self.TransactionManager(self, parent)

    def fresh_event_id(
        self,
        guild: Database.Guild,
        con: Optional[Database.TransactionManager] = None,
    ) -> int:
        assert False

    def add_event(
        self,
        event: Event,
        con: Optional[Database.TransactionManager] = None,
    ) -> None:
        assert False

    def add_guild(
        self,
        guild_id: int,
        con: Optional[Database.TransactionManager] = None,
    ) -> Database.Guild:
        assert False

    def get_guilds(
        self, con: Optional[Database.TransactionManager] = None
    ) -> List[Database.Guild]:
        assert False

    def get_guild(
        self,
        guild_id: int,
        con: Optional[Database.TransactionManager] = None,
    ) -> Database.Guild:
        assert False

    def remove_guild(
        self,
        guild: Database.Guild,
        con: Optional[Database.TransactionManager] = None,
    ) -> Database.Guild:
        assert False

    class Guild:

        def __init__(self, parent: Database, id: int):
            self.parent = parent
            self.id = id

        def __eq__(self, other: Any) -> bool:
            if isinstance(other, Database.Guild):
                return self.parent == other.parent and self.id == other.id
            return False

        def __repr__(self) -> str:
            return f"<DatabaseGuild: {self.id}>"

        def get_events(
            self,
            timestamp_start: float,
            timestamp_end: float,
            event_type: Optional[Type[Event]] = None,
            con: Optional[Database.TransactionManager] = None,
        ) -> list[Event]:
            assert False

        def remove_event(
            self,
            event: Event,
            con: Optional[Database.TransactionManager] = None,
        ) -> Event:
            assert False

        def set_config(
            self,
            config: dict[Any, Any],
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            assert False

        def get_config(
            self, con: Optional[Database.TransactionManager] = None
        ) -> dict[Any, Any]:
            assert False

        def fresh_region_id(
            self, con: Optional[Database.TransactionManager] = None
        ) -> int:
            assert False

        def add_region(
            self,
            region: Database.BasicRegion,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Region:
            assert False

        def get_regions(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.Region]:
            assert False

        def get_region(
            self,
            region_id: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Region:
            assert False

        def remove_region(
            self,
            region: Database.Region,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Region:
            assert False

        def add_player(
            self,
            player_id: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Player:
            assert False

        def get_players(self) -> List[Database.Player]:
            assert False

        def get_player(
            self,
            player_id: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Player:
            assert False

        def remove_player(
            self,
            player: Database.Player,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Player:
            assert False

        def fresh_creature_id(
            self, con: Optional[Database.TransactionManager] = None
        ) -> int:
            assert False

        def add_creature(
            self,
            creature: Database.BasicCreature,
            owner: Database.Player,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Creature:
            assert False

        def get_creatures(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.Creature]:
            assert False

        def get_creature(
            self,
            creature_id: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Creature:
            assert False

        def remove_creature(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Creature:
            assert False

        def add_to_creature_pool(
            self,
            creature: Database.BasicCreature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            assert False

        def get_creature_pool(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.BasicCreature]:
            assert False

        def get_random_from_creature_pool(
            self, con: Optional[Database.TransactionManager] = None
        ) -> Database.BasicCreature:
            assert False

        def remove_from_creature_pool(
            self,
            creature: Database.BasicCreature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            assert False

        def add_free_creature(
            self,
            creature: Database.BasicCreature,
            channel_id: int,
            message_id: int,
            roller: Database.Player,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.FreeCreature:
            assert False

        def get_free_creatures(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.FreeCreature]:
            assert False

        def get_free_creature(
            self,
            channel_id: int,
            message_id: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.FreeCreature:
            assert False

        def remove_free_creature(
            self,
            creature: Database.FreeCreature,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.FreeCreature:
            assert False

        class RegionAddedEvent(Event):

            event_type = "region_added"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                region_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.region_id = region_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Guild.RegionAddedEvent:
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
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                region_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.region_id = region_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Guild.RegionRemovedEvent:
                return Database.Guild.RegionRemovedEvent(
                    parent, id, timestamp, parent_event, guild, extra_data["region_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"region_id": self.region_id})

            def text(self) -> str:
                return f"<region:{self.region_id}> has been removed"

        class PlayerAddedEvent(Event):

            event_type = "player_added"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                player_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Guild.PlayerAddedEvent:
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
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                player_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Guild.PlayerRemovedEvent:
                return Database.Guild.PlayerRemovedEvent(
                    parent, id, timestamp, parent_event, guild, extra_data["player_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"player_id": self.player_id})

            def text(self) -> str:
                return f"<player:{self.player_id}> has left"
            
    class BasicRegion(BaseRegion):

        id = -1
        name = "default_region"
        category: Optional[RegionCategory] = None

        def __init__(self: Database.BasicRegion) -> None:
            pass

        def __repr__(self) -> str:
            return f"<BaseRegion: {self.id}#{self.name}>"

        def __eq__(self, other: Any) -> bool:
            if isinstance(other, Database.BasicRegion):
                return self.id == other.id
            return False

        def quest_effect_short_text(self) -> str:
            return ""

        def quest_effect_full_text(self) -> str:
            return ""

        def quest_effect_price(
            self,
            region_db: Database.Region,
            creature_db: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
            extra_data: dict[Any, Any] = {},
        ) -> None:
            return

        def quest_effect(
            self,
            region_db: Database.Region,
            creature_db: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
            extra_data: dict[Any, Any] = {},
        ) -> None:
            return

    class Region:

        def __init__(self, parent: Database, id: int, region: Database.BasicRegion, guild: Database.Guild):
            self.parent = parent
            self.id = id
            self.region = region
            self.guild = guild

        def __eq__(self, other: Any) -> bool:
            if isinstance(other, Database.Region):
                return (
                    self.parent == other.parent
                    and self.id == other.id
                    and self.guild.id == other.guild.id
                )
            return False

        def __repr__(self) -> str:
            return f"<DatabaseRegion: {self.region} in {self.guild}, status: {self.occupied()}>"

        def occupy(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            assert False

        def unoccupy(
            self,
            current: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            assert False

        def occupied(
            self, con: Optional[Database.TransactionManager] = None
        ) -> tuple[Optional[Database.Creature], Optional[int]]:
            assert False

        class RegionRechargeEvent(Event):

            event_type = "region_recharge"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                region_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.region_id = region_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Region.RegionRechargeEvent:
                return Database.Region.RegionRechargeEvent(
                    parent, id, timestamp, parent_event, guild, extra_data["region_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"region_id": self.region_id})

            def text(self) -> str:
                return f"{self.region_id} has recharged"

            def resolve(
                self,
                con: Optional[Database.TransactionManager] = None,
            ) -> None:
                self.guild.get_region(self.region_id).unoccupy(self.timestamp, con=con)

    class Player:

        def __init__(self, parent: Database, id: int, guild: Database.Guild):
            self.parent = parent
            self.id = id
            self.guild = guild

        def __eq__(self, other: Any) -> bool:
            if isinstance(other, Database.Player):
                return (
                    self.parent == other.parent
                    and self.guild.id == other.guild.id
                    and self.id == other.id
                )
            return False

        def __repr__(self) -> str:
            return f"<DatabasePlayer: {self.id} in {self.guild}>"

        def get_resources(
            self, con: Optional[Database.TransactionManager] = None
        ) -> dict[Resource, int]:
            assert False

        def set_resources(
            self,
            resources: dict[Resource, int],
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            assert False

        def get_deck(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.Creature]:
            assert False

        def get_hand(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.Creature]:
            assert False

        def get_discard(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.Creature]:
            assert False

        def get_played(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.Creature]:
            assert False

        def get_full_deck(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.Creature]:
            with self.parent.transaction(parent=con) as sub_con:
                return sorted(
                    self.get_deck(con=sub_con)
                    + self.get_hand(con=sub_con)
                    + self.get_discard(con=None)
                    + self.get_played(con=None),
                    key=lambda x: str(x),
                )

        def get_campaign(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Tuple[Database.Creature, int]]:
            assert False

        def get_events(
            self,
            timestamp_start: float,
            timestamp_end: float,
            event_type: Optional[Type[Event]] = None,
            con: Optional[Database.TransactionManager] = None,
        ) -> list[Event]:
            assert False

        def get_recharges(
            self, con: Optional[Database.TransactionManager] = None
        ) -> dict[str, Event]:
            recharge_event_classes: list[type[Event]] = [
                Database.Player.PlayerOrderRechargeEvent,
                Database.Player.PlayerMagicRechargeEvent,
                Database.Player.PlayerCardRechargeEvent,
            ]

            r: dict[str, Event] = {}

            for c in recharge_event_classes:
                events = self.get_events(0, time.time() * 2, event_type=c)
                assert len(events) == 1
                recharge_event = events[0]
                r[c.event_type] = recharge_event

            return r

        def has(
            self,
            resource: Resource,
            amount: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> bool:
            return self.fulfills_price([Price(resource, amount)], con=con)

        def give(
            self,
            resource: Resource,
            amount: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            self.gain([Gain(resource, amount)], con=con)

        def remove(
            self,
            resource: Resource,
            amount: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            self.pay_price([Price(resource, amount)], con=con)

        def fulfills_price(
            self,
            price: list[Price],
            con: Optional[Database.TransactionManager] = None,
        ) -> bool:
            merged_prices: dict[Resource, int] = defaultdict(lambda: 0)
            for p in price:
                if p.amount == 0:
                    continue

                merged_prices[p.resource] += p.amount

            if len(merged_prices) == 0:
                return True

            with self.parent.transaction(parent=con) as sub_con:
                resources: dict[Resource, int] = self.get_resources(con=sub_con)
                hand_size: int = len(self.get_hand(con=sub_con))

            for r, a in merged_prices.items():
                if r in BaseResources:
                    if resources[r] < a:
                        return False
            return True

        def _delete_creatures(
            self,
            hand_size: int,
            a: int,
            extra_data: dict[Any, Any],
            con: Optional[Database.TransactionManager] = None,
        ) -> None:

            with self.parent.transaction(parent=con) as sub_con:
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
                        assert self.guild.get_creature(creature_id, con=sub_con).owner == self
                except Exception as e:
                    raise BadExtraData(str(e), extra_data=expected_extra_data)

                # like this extra_data can be further propagated
                creatures_to_delete = creatures_to_delete[:a]
                extra_data["creatures_to_delete"] = creatures_to_delete

                for c in creatures_to_delete:
                    self.delete_creature_from_hand(c)

        def gain(
            self,
            gain: list[Gain],
            con: Optional[Database.TransactionManager] = None,
            extra_data: dict[Any, Any] = {},
        ) -> None:
            merged_gains: dict[Resource, int] = defaultdict(lambda: 0)
            for g in gain:
                if g.amount == 0:
                    continue
                merged_gains[g.resource] += g.amount

            if len(merged_gains) == 0:
                return

            with self.parent.transaction(parent=con) as sub_con:
                event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                sub_con.add_event(
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

                resources: dict[Resource, int] = self.get_resources(con=sub_con)
                hand_size: int = len(self.get_hand(con=sub_con))

                for r, a in merged_gains.items():
                    if r in BaseResources:
                        resources[r] += a

                self.set_resources(resources, con=sub_con)

        def pay_price(
            self,
            price: list[Price],
            con: Optional[Database.TransactionManager] = None,
            extra_data: dict[Any, Any] = {},
        ) -> None:
            merged_price: dict[Resource, int] = defaultdict(lambda: 0)
            for p in price:
                if p.amount == 0:
                    continue
                merged_price[p.resource] += p.amount

            if len(merged_price) == 0:
                return

            with self.parent.transaction(parent=con) as sub_con:
                event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                sub_con.add_event(
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

                resources: dict[Resource, int] = self.get_resources(con=sub_con)
                hand_size = len(self.get_hand(con=sub_con))

                for r, a in merged_price.items():
                    if r in BaseResources:
                        if resources[r] < a:
                            raise NotEnoughResourcesException(
                                "Player is paying {} {} but only has {}".format(a, r, resources[r])
                            )
                        resources[r] -= a
                self.set_resources(resources, con=sub_con)

        def draw_card_raw(
            self, con: Optional[Database.TransactionManager] = None
        ) -> Database.Creature:
            assert False

        def reshuffle_discard(
            self, con: Optional[Database.TransactionManager] = None
        ) -> None:
            pass

        def draw_cards(
            self,
            N: int = 1,
            con: Optional[Database.TransactionManager] = None,
        ) -> tuple[List[Database.Creature], bool, bool]:
            with self.parent.transaction(parent=con) as sub_con:
                max_cards = self.guild.get_config(con=sub_con)["max_cards"]
                current_cards = len(self.get_hand(con=sub_con))

                cards_drawn: List[Database.Creature] = []
                discard_reshuffled = False
                hand_full = False
                for _ in range(N):
                    assert current_cards + len(cards_drawn) <= max_cards

                    if current_cards + len(cards_drawn) == max_cards:
                        hand_full = True
                        break

                    if len(self.get_deck(con=sub_con)) == 0:
                        self.reshuffle_discard(con=sub_con)
                        discard_reshuffled = True

                        if len(self.get_deck(con=sub_con)) == 0:
                            break

                    card = self.draw_card_raw(con=sub_con)
                    cards_drawn.append(card)

                event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                sub_con.add_event(
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

        def delete_creature_from_hand(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            pass

        def recharge_creature(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            pass

        def discard_creature_from_hand(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            pass

        def play_creature(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            pass

        def campaign_creature(
            self,
            creature: Database.Creature,
            strength: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            pass

        def add_to_discard(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            pass

        def play_creature_to_region(
            self,
            creature: Database.Creature,
            region: Database.Region,
            con: Optional[Database.TransactionManager] = None,
            extra_data: dict[Any, Any] = {},
        ) -> None:

            if region.region.category not in creature.creature.quest_region_categories:
                raise CreatureCannotQuestHere(
                    f"Region is {region.region.category} but creature can only go to {creature.creature.quest_region_categories}"
                )

            base_region: Database.BasicRegion = region.region
            base_creature: Database.BasicCreature = creature.creature

            with self.parent.transaction(parent=con) as sub_con:
                event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                sub_con.add_event(
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

                self.pay_price([Price(Resource.ORDERS, 1)], con=sub_con)
                base_creature.quest_ability_effect_price(
                    region, creature, con=sub_con, extra_data=extra_data
                )
                base_region.quest_effect_price(region, creature, con=sub_con, extra_data=extra_data)
                self.play_creature(creature, con=sub_con)
                region.occupy(creature, con=sub_con)
                creature.play(con=sub_con)
                base_region.quest_effect(region, creature, con=sub_con, extra_data=extra_data)
                base_creature.quest_ability_effect(
                    region, creature, con=sub_con, extra_data=extra_data
                )

        def play_creature_to_campaign(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
            extra_data: dict[Any, Any] = {},
        ) -> None:

            base_creature: Database.BasicCreature = creature.creature

            with self.parent.transaction(parent=con) as sub_con:
                event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                sub_con.add_event(
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
                    creature, con=sub_con, extra_data=extra_data
                )
                strength = base_creature.campaign_ability_effect(
                    creature, con=sub_con, extra_data=extra_data
                )
                self.campaign_creature(creature, strength, con=sub_con)

        class PlayerDrawEvent(Event):

            event_type = "player_draw"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                player_id: int,
                num_cards: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id
                self.num_cards = num_cards

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerDrawEvent:
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
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                player_id: int,
                changes: List[Tuple[int, int]],
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id
                self.changes = changes

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerGainEvent:
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
                gain_string = resource_changes_to_string(
                    list(map(lambda x: Gain(resource=Resource(x[0]), amount=x[1]), self.changes)),
                    third_person=True,
                )
                return f"<player:{self.player_id}> {gain_string}"

        class PlayerPayEvent(Event):

            event_type = "player_pay"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                player_id: int,
                changes: List[Tuple[int, int]],
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id
                self.changes = changes

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerPayEvent:
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
                gain_string = resource_changes_to_string(
                    list(map(lambda x: Price(resource=Resource(x[0]), amount=x[1]), self.changes)),
                    third_person=True,
                )
                return f"<player:{self.player_id}> {gain_string}"

        class PlayerPlayToRegionEvent(Event):

            event_type = "player_play_to_region"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                player_id: int,
                creature_id: int,
                region_id: int,
                play_extra_data: dict[Any, Any],
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id
                self.creature_id = creature_id
                self.region_id = region_id
                self.play_extra_data = play_extra_data

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerPlayToRegionEvent:
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
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                player_id: int,
                creature_id: int,
                play_extra_data: dict[Any, Any],
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id
                self.creature_id = creature_id
                self.play_extra_data = play_extra_data

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerPlayToCampaignEvent:
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
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                player_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerOrderRechargeEvent:
                return Database.Player.PlayerOrderRechargeEvent(
                    parent, id, timestamp, parent_event, guild, extra_data["player_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"player_id": self.player_id})

            def text(self) -> str:
                return f"<player:{self.player_id}> recharges on orders"

            def resolve(
                self,
                con: Optional[Database.TransactionManager] = None,
            ) -> None:
                with self.parent.transaction(parent=con) as sub_con:
                    player: Database.Player = self.guild.get_player(self.player_id, con=sub_con)
                    guild_config = self.guild.get_config(con=sub_con)
                    player_orders = player.get_resources(con=sub_con)[Resource.ORDERS]
                    if player_orders + 1 <= guild_config["max_orders"]:
                        player.gain([Gain(resource=Resource.ORDERS, amount=1)], con=sub_con)

                    event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                    sub_con.add_event(
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
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                player_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerMagicRechargeEvent:
                return Database.Player.PlayerMagicRechargeEvent(
                    parent, id, timestamp, parent_event, guild, extra_data["player_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"player_id": self.player_id})

            def text(self) -> str:
                return f"<player:{self.player_id}> recharges on magic"

            def resolve(
                self,
                con: Optional[Database.TransactionManager] = None,
            ) -> None:
                with self.parent.transaction(parent=con) as sub_con:
                    player: Database.Player = self.guild.get_player(self.player_id, con=sub_con)
                    guild_config = self.guild.get_config(con=sub_con)
                    player_magic = player.get_resources(con=sub_con)[Resource.MAGIC]
                    if player_magic + 1 <= guild_config["max_magic"]:
                        player.gain([Gain(resource=Resource.MAGIC, amount=1)], con=sub_con)

                    event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                    sub_con.add_event(
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
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                player_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.player_id = player_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerCardRechargeEvent:
                return Database.Player.PlayerCardRechargeEvent(
                    parent, id, timestamp, parent_event, guild, extra_data["player_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"player_id": self.player_id})

            def text(self) -> str:
                return f"<player:{self.player_id}> recharges on cards"

            def resolve(
                self,
                con: Optional[Database.TransactionManager] = None,
            ) -> None:
                with self.parent.transaction(parent=con) as sub_con:
                    player: Database.Player = self.guild.get_player(self.player_id, con=sub_con)
                    guild_config = self.guild.get_config(con=sub_con)
                    player.draw_cards(1, con=sub_con)

                    event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                    sub_con.add_event(
                        Database.Player.PlayerCardRechargeEvent(
                            self.parent,
                            event_id,
                            time.time() + guild_config["card_recharge"],
                            None,
                            self.guild,
                            self.player_id,
                        ),
                    )


    class BasicCreature(BaseCreature):

        id = -1
        name = "default_creature"
        quest_region_categories: list[RegionCategory] = []
        claim_cost: int = 0

        def __init__(self: Database.BasicCreature):
            assert False

        def __repr__(self) -> str:
            return f"<BaseCreature: {self.name}>"

        def __eq__(self, other: Any) -> bool:
            if isinstance(other, BaseCreature):
                return str(self) == str(other)
            return False

        # questing
        def quest_ability_effect_short_text(self) -> str:
            assert False

        def quest_ability_effect_full_text(self) -> str:
            assert False

        def quest_ability_effect_price(
            self,
            region_db: Database.Region,
            creature_db: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
            extra_data: dict[Any, Any] = {},
        ) -> None:
            assert False

        def quest_ability_effect(
            self,
            region_db: Database.Region,
            creature_db: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
            extra_data: dict[Any, Any] = {},
        ) -> None:
            assert False

        # campaigning
        def campaign_ability_effect_short_text(self) -> str:
            assert False

        def campaign_ability_effect_full_text(self) -> str:
            assert False

        def campaign_ability_effect_price(
            self, creature_db: Database.Creature, con: Optional[Database.TransactionManager] = None, extra_data: dict[Any, Any] = {}
        ) -> None:
            assert False

        def campaign_ability_effect(
            self, creature_db: Database.Creature, con: Optional[Database.TransactionManager] = None, extra_data: dict[Any, Any] = {}
        ) -> int:
            assert False


    class Creature:

        def __init__(
            self,
            parent: Database,
            id: int,
            creature: Database.BasicCreature,
            guild: Database.Guild,
            owner: Database.Player,
        ):
            self.parent = parent
            self.id = id
            self.creature = creature
            self.guild = guild
            self.owner = owner

        def __eq__(self, other: Any) -> bool:
            if isinstance(other, Database.Creature):
                return (
                    self.parent == other.parent
                    and self.guild.id == other.guild.id
                    and self.id == other.id
                )
            return False

        def __repr__(self) -> str:
            return f"<DatabaseCreature: {self.creature} in {self.guild} as {self.id} owned by {self.owner}>"

        def play(
            self, con: Optional[Database.TransactionManager] = None
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                until = self.parent.timestamp_after(self.guild.get_config()["creature_recharge"])

                event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
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
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                creature_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.creature_id = creature_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Creature.CreatureRechargeEvent:
                return Database.Creature.CreatureRechargeEvent(
                    parent, id, timestamp, parent_event, guild, extra_data["creature_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"creature_id": self.creature_id})

            def text(self) -> str:
                return "{creature_id} has recharged"

            def resolve(
                self,
                con: Optional[Database.TransactionManager] = None,
            ) -> None:
                with self.parent.transaction(parent=con) as sub_con:
                    creature = self.guild.get_creature(self.creature_id)
                    creature.owner.recharge_creature(creature)

    class FreeCreature:

        def __init__(
            self,
            parent: Database,
            creature: Database.BasicCreature,
            guild: Database.Guild,
            channel_id: int,
            message_id: int,
            roller_id: int,
            timestamp_protected: float,
            timestamp_expires: float,
        ):
            self.parent = parent
            self.guild = guild
            self.creature = creature
            self.roller_id = roller_id
            self.channel_id = channel_id
            self.message_id = message_id

        def __eq__(self, other: Any) -> bool:
            if isinstance(other, Database.FreeCreature):
                return (
                    self.parent == other.parent
                    and self.creature == other.creature
                    and self.guild.id == other.guild.id
                    and self.channel_id == other.channel_id
                    and self.message_id == other.message_id
                )
            return False

        def create_events(
            self, con: Optional[Database.TransactionManager] = None
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                # Notice that we add the events to the parent directly instead of the connection
                # that is because we do not want these events to be part of the transaction
                event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                self.parent.add_event(
                    Database.FreeCreature.FreeCreatureProtectedEvent(
                        self.parent,
                        event_id,
                        self.get_protected_timestamp(con=sub_con),
                        None,
                        self.guild,
                        self.channel_id,
                        self.message_id,
                    )
                )

                event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                self.parent.add_event(
                    Database.FreeCreature.FreeCreatureExpiresEvent(
                        self.parent,
                        event_id,
                        self.get_expires_timestamp(con=sub_con),
                        None,
                        self.guild,
                        self.channel_id,
                        self.message_id,
                    )
                )

        def get_protected_timestamp(
            self, con: Optional[Database.TransactionManager] = None
        ) -> int:
            return -1

        def get_expires_timestamp(
            self, con: Optional[Database.TransactionManager] = None
        ) -> int:
            return -1

        def is_protected(
            self,
            timestamp: float,
            con: Optional[Database.TransactionManager] = None,
        ) -> bool:
            return self.get_protected_timestamp(con=con) > timestamp

        def is_expired(
            self,
            timestamp: float,
            con: Optional[Database.TransactionManager] = None,
        ) -> bool:
            return self.get_expires_timestamp(con=con) < timestamp

        def claim(
            self,
            timestamp: float,
            owner: Database.Player,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Creature:

            self.guild.get_free_creature(self.channel_id, self.message_id)

            if self.is_expired(timestamp):
                raise ExpiredFreeCreature()

            if self.is_protected(timestamp) and owner.id != self.roller_id:
                raise ProtectedFreeCreature(
                    f"This creature is protected until {self.get_protected_timestamp()}"
                )

            with self.parent.transaction(parent=con) as sub_con:
                owner.pay_price([Price(Resource.RALLY, self.creature.claim_cost)], con=sub_con)
                # dont do this for now so that information about claimed creatures can still be queried
                # guild.remove_free_creature(self, con=sub_con)
                creature = self.guild.add_creature(self.creature, owner, con=sub_con)
                owner.add_to_discard(creature, con=sub_con)

                event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                sub_con.add_event(
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

                return creature

        class FreeCreatureProtectedEvent(Event):

            event_type = "free_creature_protected"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                channel_id: int,
                message_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.channel_id = channel_id
                self.message_id = message_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.FreeCreature.FreeCreatureProtectedEvent:
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
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                channel_id: int,
                message_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event, guild)
                self.channel_id = channel_id
                self.message_id = message_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.FreeCreature.FreeCreatureExpiresEvent:
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

            def resolve(
                self,
                con: Optional[Database.TransactionManager] = None,
            ) -> None:
                with self.parent.transaction(parent=con) as sub_con:
                    try:
                        free_creature: Database.FreeCreature = self.guild.get_free_creature(
                            self.channel_id, self.message_id, con=sub_con
                        )
                        self.guild.remove_free_creature(free_creature, con=sub_con)
                    except CreatureNotFound:
                        pass

        class FreeCreatureClaimedEvent(Event):

            event_type = "free_creature_claimed"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Optional[Event],
                guild: Database.Guild,
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

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event: Event,
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.FreeCreature.FreeCreatureClaimedEvent:
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
