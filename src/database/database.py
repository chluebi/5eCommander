from __future__ import annotations

import time
import json
import copy
import math
import random
from typing import List, Tuple, Type, Optional, Union, Any, cast, Generic, TypeVar, TYPE_CHECKING
from collections import defaultdict

from src.core.base_types import (
    Resource,
    Price,
    Gain,
    BaseResources,
    Event,
    RegionCategory,
    resource_changes_to_string,
    resource_changes_to_short_string,
    resource_to_emoji,
)
from src.core.exceptions import (
    NotEnoughResourcesException,
    CreatureCannotQuestHere,
    ExpiredFreeCreature,
    ProtectedFreeCreature,
    CreatureNotFound,
)

if TYPE_CHECKING:
    from src.definitions.extra_data import EXTRA_DATA


from sqlalchemy import RootTransaction, Connection


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

                if parent.events != [] and event.parent_event_id is None:
                    event.parent_event_id = parent.events[-1].id

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

    def get_guilds(self, con: Optional[Database.TransactionManager] = None) -> List[Database.Guild]:
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

    class StartCondition:
        def __init__(
            self,
            start_config: dict[Any, Any],
            start_active_regions: list[Database.BaseRegion],
            start_available_creatures: list[Database.BaseCreature],
            start_deck: list[Database.BaseCreature],
        ):
            self.start_config = start_config
            self.start_active_regions = start_active_regions
            self.start_available_creatures = start_available_creatures
            self.start_deck = start_deck

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
            also_resolved: Optional[bool] = True,
            con: Optional[Database.TransactionManager] = None,
        ) -> list[Event]:
            assert False

        def get_event_by_id(
            self,
            event_id: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> Event:
            assert False

        def mark_event_as_resolved(
            self, event: Event, con: Optional[Database.TransactionManager] = None
        ) -> None:
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

        def get_config(self, con: Optional[Database.TransactionManager] = None) -> dict[Any, Any]:
            assert False

        def fresh_region_id(self, con: Optional[Database.TransactionManager] = None) -> int:
            assert False

        def add_region(
            self,
            region: Database.BaseRegion,
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

        def get_players(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.Player]:
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

        def fresh_creature_id(self, con: Optional[Database.TransactionManager] = None) -> int:
            assert False

        def add_creature(
            self,
            creature: Database.BaseCreature,
            owner: Database.Player,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Creature:
            assert False

        def get_creatures(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.Creature]:
            assert False

        def get_basecreatures(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.BaseCreature]:
            assert False

        def get_all_obtainable_basecreatures(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.BaseCreature]:
            basecreatures = self.get_basecreatures(con=con)
            all_creatures = copy.copy(basecreatures)

            for c in basecreatures:
                for related in c.related_creatures:
                    if related not in all_creatures:
                        all_creatures.append(related)

            for r in self.get_regions(con=con):
                for related in r.region.related_creatures:
                    if related not in all_creatures:
                        all_creatures.append(related)

            return all_creatures

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
            creature: Database.BaseCreature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            assert False

        def get_creature_pool(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.BaseCreature]:
            assert False

        def get_random_from_creature_pool(
            self, con: Optional[Database.TransactionManager] = None
        ) -> Database.BaseCreature:
            assert False

        def roll_creature(
            self, con: Optional[Database.TransactionManager] = None
        ) -> Database.BaseCreature:
            creature = self.get_random_from_creature_pool(con=con)
            i = 0
            while i < 10:
                if (
                    1 / math.pow(creature.claim_cost + 1, 0.13 * creature.claim_cost)
                    > random.random()
                ):
                    break
                creature = self.get_random_from_creature_pool(con=con)

            return creature

        def remove_from_creature_pool(
            self,
            creature: Database.BaseCreature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            assert False

        def add_free_creature(
            self,
            creature: Database.BaseCreature,
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

        class GuildCreatedEvent(Event):
            event_type = "guild_created"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Guild.GuildCreatedEvent:
                return Database.Guild.GuildCreatedEvent(
                    parent, id, timestamp, parent_event_id, guild
                )

            def extra_data(self) -> str:
                return json.dumps({})

            def text(self) -> str:
                return "This guild has been created"

        class RegionAddedEvent(Event):
            event_type = "region_added"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                region_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.region_id = region_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Guild.RegionAddedEvent:
                return Database.Guild.RegionAddedEvent(
                    parent, id, timestamp, parent_event_id, guild, extra_data["region_id"]
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
                parent_event_id: Optional[int],
                guild: Database.Guild,
                region_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.region_id = region_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Guild.RegionRemovedEvent:
                return Database.Guild.RegionRemovedEvent(
                    parent, id, timestamp, parent_event_id, guild, extra_data["region_id"]
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
                parent_event_id: Optional[int],
                guild: Database.Guild,
                player_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.player_id = player_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Guild.PlayerAddedEvent:
                return Database.Guild.PlayerAddedEvent(
                    parent, id, timestamp, parent_event_id, guild, extra_data["player_id"]
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
                parent_event_id: Optional[int],
                guild: Database.Guild,
                player_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.player_id = player_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Guild.PlayerRemovedEvent:
                return Database.Guild.PlayerRemovedEvent(
                    parent, id, timestamp, parent_event_id, guild, extra_data["player_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"player_id": self.player_id})

            def text(self) -> str:
                return f"<player:{self.player_id}> has left"

        class ConflictStartEvent(Event):
            event_type = "conflict_start"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Guild.ConflictStartEvent:
                return Database.Guild.ConflictStartEvent(
                    parent, id, timestamp, parent_event_id, guild
                )

            def extra_data(self) -> str:
                return json.dumps({})

            def text(self) -> str:
                return "A new conflict has started!"

            def resolve(self, con: Any) -> None:
                con = cast(Database.TransactionManager, con)
                self.parent = cast(Database, self.parent)
                self.guild = cast(Database.Guild, self.guild)

                with self.parent.transaction(parent=con) as sub_con:
                    until = self.parent.timestamp_after(
                        self.guild.get_config(con=sub_con)["conflict_duration"]
                    )

                    event_id = self.parent.fresh_event_id(self.guild, con=sub_con)

                    con.add_event(
                        Database.Guild.ConflictEndEvent(
                            self.parent, event_id, until, None, self.guild
                        ),
                    )

        class ConflictEndEvent(Event):
            event_type = "conflict_end"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Guild.ConflictEndEvent:
                return Database.Guild.ConflictEndEvent(
                    parent, id, timestamp, parent_event_id, guild
                )

            def extra_data(self) -> str:
                return json.dumps({})

            def text(self) -> str:
                return "The conflict has ended, all campaigning creatures are returned."

            def resolve(self, con: Any) -> None:
                con = cast(Database.TransactionManager, con)
                self.parent = cast(Database, self.parent)
                self.guild = cast(Database.Guild, self.guild)

                with self.parent.transaction(parent=con) as sub_con:
                    player_scores: dict[int, int] = {}
                    players = self.guild.get_players(con=sub_con)

                    if len(players) > 0:
                        for player_db in self.guild.get_players(con=sub_con):
                            player_strength = 0

                            for c, s in player_db.get_campaign(con=sub_con):
                                player_db.uncampaign_creature(c, con=sub_con)
                                player_strength += s

                            player_scores[player_db.id] = player_strength

                        event_id = self.parent.fresh_event_id(self.guild, con=sub_con)

                        sub_con.add_event(
                            Database.Guild.ConflictResultEvent(
                                self.parent,
                                event_id,
                                time.time(),
                                None,
                                self.guild,
                                list(
                                    map(
                                        list,
                                        sorted(
                                            player_scores.items(), key=lambda x: x[1], reverse=True
                                        ),
                                    )
                                ),
                            ),
                        )

                    event_id = self.parent.fresh_event_id(self.guild, con=sub_con)

                    sub_con.add_event(
                        Database.Guild.ConflictStartEvent(
                            self.parent, event_id, time.time(), None, self.guild
                        ),
                    )

        class ConflictResultEvent(Event):
            event_type = "conflict_result"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                scores: List[List[int]],
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.scores = scores

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Guild.ConflictResultEvent:
                return Database.Guild.ConflictResultEvent(
                    parent, id, timestamp, parent_event_id, guild, extra_data["scores"]
                )

            def extra_data(self) -> str:
                return json.dumps({"scores": self.scores})

            def text(self) -> str:
                winner, winner_strength = cast(Tuple[int, int], tuple(self.scores[0]))
                winner_text = f"<player:{winner}> has won"
                ranking_text = "\n".join(
                    [
                        f"#{i} <player:{p}>: {score} {resource_to_emoji(Resource.STRENGTH)}"
                        for i, (p, score) in enumerate(self.scores, 1)
                    ]
                )
                return f"**{winner_text}**\n\n{ranking_text}"

    class BaseRegion:
        id = -1
        name = "default_region"
        category: Optional[RegionCategory] = None
        related_creatures: List[Database.BaseCreature] = []

        def __init__(self: Database.BaseRegion) -> None:
            return

        def __repr__(self) -> str:
            return f"<BaseRegion: {self.id}#{self.name}>"

        def __eq__(self, other: Any) -> bool:
            if isinstance(other, Database.BaseRegion):
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
            extra_data: EXTRA_DATA = [],
        ) -> None:
            return

        def quest_effect(
            self,
            region_db: Database.Region,
            creature_db: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
            extra_data: EXTRA_DATA = [],
        ) -> None:
            return

    class Region:
        def __init__(
            self, parent: Database, id: int, region: Database.BaseRegion, guild: Database.Guild
        ):
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

        def text(self) -> str:
            assert self.region.category is not None
            return f"{self.region.category.emoji} {self.region.name.title()}"

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
                parent_event_id: Optional[int],
                guild: Database.Guild,
                region_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.region_id = region_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Region.RegionRechargeEvent:
                return Database.Region.RegionRechargeEvent(
                    parent, id, timestamp, parent_event_id, guild, extra_data["region_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"region_id": self.region_id})

            def text(self) -> str:
                return f"<region:{self.region_id}> has recharged"

            def resolve(
                self,
                con: Optional[Database.TransactionManager] = None,
            ) -> None:
                self.guild = cast(Database.Guild, self.guild)
                self.guild.get_region(self.region_id).unoccupy(int(time.time()), con=con)

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
        ) -> List[Tuple[Database.Creature, int]]:
            assert False

        def get_full_deck(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.Creature]:
            with self.parent.transaction(parent=con) as sub_con:
                return sorted(
                    self.get_deck(con=sub_con)
                    + self.get_hand(con=sub_con)
                    + self.get_discard(con=None)
                    + list(map(lambda x: x[0], self.get_played(con=None))),
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
            also_resolved: Optional[bool] = True,
            con: Optional[Database.TransactionManager] = None,
        ) -> list[Event]:
            assert False

        def test_recharges(
            self, con: Optional[Database.TransactionManager] = None
        ) -> dict[str, List[Event]]:
            recharge_event_classes: list[type[Event]] = [
                Database.Player.PlayerOrderRechargeEvent,
                Database.Player.PlayerMagicRechargeEvent,
                Database.Player.PlayerCardRechargeEvent,
            ]

            r: dict[str, List[Event]] = {}

            for c in recharge_event_classes:
                events = self.get_events(
                    0, time.time() * 2, event_type=c, also_resolved=False, con=con
                )
                r[c.event_type] = events

            return r

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
                events = self.get_events(
                    0, time.time() * 2, event_type=c, also_resolved=False, con=con
                )

                recharge_event = sorted(events, key=lambda x: x.timestamp)[0]
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

        def gain(self, gain: list[Gain], con: Optional[Database.TransactionManager] = None) -> None:
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
            self, price: list[Price], con: Optional[Database.TransactionManager] = None
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

        def reshuffle_discard(self, con: Optional[Database.TransactionManager] = None) -> None:
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

                if len(cards_drawn) > 0:
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

        def create_creature_in_hand(
            self,
            creature: Database.BaseCreature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                sub_con.add_event(
                    Database.Player.PlayerCreateCreatureEvent(
                        self.parent, event_id, time.time(), None, self.guild, self.id, creature.id
                    )
                )

                new_creature = self.guild.add_creature(creature, self, con=sub_con)
                self.add_creature_to_hand(new_creature, con=sub_con)

        def remove_creature_from_deck(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            assert False

        def draw_creature_from_deck(
            self, creature: Database.Creature, con: Optional[Database.TransactionManager] = None
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                sub_con.add_event(
                    Database.Player.PlayerDrawCreatureEvent(
                        self.parent, event_id, time.time(), None, self.guild, self.id, creature.id
                    )
                )

                if creature not in self.get_deck(con=sub_con):
                    raise CreatureNotFound("Creature not found in deck")

                self.remove_creature_from_deck(creature, con=con)
                self.add_creature_to_hand(creature, con=con)

        def add_creature_to_hand(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            pass

        def remove_creature_from_hand(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            pass

        def delete_creature_in_hand(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                sub_con.add_event(
                    Database.Player.PlayerDeleteCreatureEvent(
                        self.parent, event_id, time.time(), None, self.guild, self.id, creature.id
                    )
                )

                creatures = self.get_hand(con=sub_con)
                if creature not in creatures:
                    raise CreatureNotFound("Creature not found in hand (delete from hand)")
                self.remove_creature_from_hand(creature, con=sub_con)

        def remove_creature_from_played(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            pass

        def delete_creature_in_played(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                sub_con.add_event(
                    Database.Player.PlayerDeleteCreatureEvent(
                        self.parent, event_id, time.time(), None, self.guild, self.id, creature.id
                    )
                )

                creatures = [c for c, _ in self.get_played(con=sub_con)]
                if creature not in creatures:
                    raise CreatureNotFound("Creature not found in played")
                self.remove_creature_from_played(creature, con=sub_con)

        def recharge_creature(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                creatures = [c for c, _ in self.get_played(con=sub_con)]
                if creature not in creatures:
                    raise CreatureNotFound("Creature not found in played")
                self.remove_creature_from_played(creature, con=sub_con)
                self.add_to_discard(creature, con=sub_con)

        def discard_creature_from_hand(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                sub_con.add_event(
                    Database.Player.PlayerDiscardCreatureEvent(
                        self.parent, event_id, time.time(), None, self.guild, self.id, creature.id
                    )
                )

                creatures = self.get_hand(con=sub_con)
                if creature not in creatures:
                    raise CreatureNotFound("Creature not found in hand (discard_creature)")
                self.remove_creature_from_hand(creature, con=sub_con)
                self.add_to_discard(creature, con=sub_con)

        def add_creature_to_played(
            self,
            creature: Database.Creature,
            until: float,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            pass

        def play_creature(
            self,
            creature: Database.Creature,
            until: float,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                creatures = self.get_hand(con=sub_con)
                if creature not in creatures:
                    raise CreatureNotFound("Creature not found in hand (play_creature)")
                self.remove_creature_from_hand(creature, con=sub_con)
                self.add_creature_to_played(creature, until, con=sub_con)

        def add_creature_to_campaign(
            self,
            creature: Database.Creature,
            strength: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            pass

        def campaign_creature(
            self,
            creature: Database.Creature,
            strength: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                creatures = self.get_hand(con=sub_con)
                if creature not in creatures:
                    raise CreatureNotFound("Creature not found in hand (campaign_creature)")
                self.remove_creature_from_hand(creature, con=sub_con)
                self.add_creature_to_campaign(creature, strength, con=sub_con)

        def remove_creature_from_campaign(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            pass

        def uncampaign_creature(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                creatures = [c for c, _ in self.get_campaign(con=sub_con)]
                if creature not in creatures:
                    raise CreatureNotFound("Creature not found in campaign")
                self.remove_creature_from_campaign(creature, con=sub_con)
                self.add_to_discard(creature, con=sub_con)

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
            extra_data: EXTRA_DATA = [],
        ) -> None:
            if region.region.category not in creature.creature.quest_region_categories:
                raise CreatureCannotQuestHere(
                    f"Region is {region.region.category} but creature can only go to {creature.creature.quest_region_categories}"
                )

            base_region: Database.BaseRegion = region.region
            base_creature: Database.BaseCreature = creature.creature

            with self.parent.transaction(parent=con) as sub_con:
                until = self.parent.timestamp_after(self.guild.get_config()["creature_recharge"])

                sub_con.add_event(
                    Database.Creature.CreatureRechargeEvent(
                        self.parent,
                        self.parent.fresh_event_id(self.guild, con=sub_con),
                        until,
                        None,
                        self.guild,
                        creature.id,
                    )
                )

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
                        {},
                    )
                )

                self.pay_price([Price(Resource.ORDERS, 1)], con=sub_con)
                base_creature.quest_ability_effect_price(
                    region, creature, con=sub_con, extra_data=extra_data
                )
                base_region.quest_effect_price(region, creature, con=sub_con, extra_data=extra_data)
                self.play_creature(creature, until, con=sub_con)
                region.occupy(creature, con=sub_con)
                base_region.quest_effect(region, creature, con=sub_con, extra_data=extra_data)
                base_creature.quest_ability_effect(
                    region, creature, con=sub_con, extra_data=extra_data
                )

        def play_creature_to_campaign(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
            extra_data: EXTRA_DATA = [],
        ) -> None:
            base_creature: Database.BaseCreature = creature.creature

            with self.parent.transaction(parent=con) as sub_con:
                event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                event = Database.Player.PlayerPlayToCampaignEvent(
                    self.parent,
                    event_id,
                    time.time(),
                    None,
                    self.guild,
                    self.id,
                    creature.id,
                    0,
                    [],
                )
                sub_con.add_event(event)

                base_creature.campaign_ability_effect_price(
                    creature, con=sub_con, extra_data=extra_data
                )
                strength = base_creature.campaign_ability_effect(
                    creature, con=sub_con, extra_data=extra_data
                )
                event.strength = strength
                self.campaign_creature(creature, strength, con=sub_con)

        class PlayerDrawEvent(Event):
            event_type = "player_draw"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                player_id: int,
                num_cards: int,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.player_id = player_id
                self.num_cards = num_cards

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerDrawEvent:
                return Database.Player.PlayerDrawEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event_id,
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
                parent_event_id: Optional[int],
                guild: Database.Guild,
                player_id: int,
                changes: List[Tuple[int, int]],
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.player_id = player_id
                self.changes = changes

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerGainEvent:
                return Database.Player.PlayerGainEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event_id,
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
                parent_event_id: Optional[int],
                guild: Database.Guild,
                player_id: int,
                changes: List[Tuple[int, int]],
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.player_id = player_id
                self.changes = changes

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerPayEvent:
                return Database.Player.PlayerPayEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event_id,
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

        class PlayerCreateCreatureEvent(Event):
            event_type = "player_create_creature"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                player_id: int,
                creature_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.player_id = player_id
                self.creature_id = creature_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerCreateCreatureEvent:
                return Database.Player.PlayerCreateCreatureEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event_id,
                    guild,
                    extra_data["player_id"],
                    extra_data["creature_id"],
                )

            def extra_data(self) -> str:
                return json.dumps({"player_id": self.player_id, "creature_id": self.creature_id})

            def text(self) -> str:
                return f"<player:{self.player_id}> receives <creature:{self.creature_id}>"

        class PlayerDrawCreatureEvent(Event):
            event_type = "player_draw_creature"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                player_id: int,
                creature_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.player_id = player_id
                self.creature_id = creature_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerDrawCreatureEvent:
                return Database.Player.PlayerDrawCreatureEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event_id,
                    guild,
                    extra_data["player_id"],
                    extra_data["creature_id"],
                )

            def extra_data(self) -> str:
                return json.dumps({"player_id": self.player_id, "creature_id": self.creature_id})

            def text(self) -> str:
                return f"<player:{self.player_id}> draws <creature:{self.creature_id}> from deck"

        class PlayerDiscardCreatureEvent(Event):
            event_type = "player_discard_creature"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                player_id: int,
                creature_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.player_id = player_id
                self.creature_id = creature_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerDiscardCreatureEvent:
                return Database.Player.PlayerDiscardCreatureEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event_id,
                    guild,
                    extra_data["player_id"],
                    extra_data["creature_id"],
                )

            def extra_data(self) -> str:
                return json.dumps({"player_id": self.player_id, "creature_id": self.creature_id})

            def text(self) -> str:
                return f"<player:{self.player_id}> discards <creature:{self.creature_id}>"

        class PlayerDeleteCreatureEvent(Event):
            event_type = "player_delete_creature"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                player_id: int,
                creature_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.player_id = player_id
                self.creature_id = creature_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerDeleteCreatureEvent:
                return Database.Player.PlayerDeleteCreatureEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event_id,
                    guild,
                    extra_data["player_id"],
                    extra_data["creature_id"],
                )

            def extra_data(self) -> str:
                return json.dumps({"player_id": self.player_id, "creature_id": self.creature_id})

            def text(self) -> str:
                return f"<player:{self.player_id}> destroys <creature:{self.creature_id}>"

        class PlayerPlayToRegionEvent(Event):
            event_type = "player_play_to_region"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                player_id: int,
                creature_id: int,
                region_id: int,
                play_extra_data: dict[Any, Any],
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.player_id = player_id
                self.creature_id = creature_id
                self.region_id = region_id
                self.play_extra_data = play_extra_data

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerPlayToRegionEvent:
                return Database.Player.PlayerPlayToRegionEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event_id,
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
                parent_event_id: Optional[int],
                guild: Database.Guild,
                player_id: int,
                creature_id: int,
                strength: int,
                play_extra_data: EXTRA_DATA,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.player_id = player_id
                self.creature_id = creature_id
                self.strength = strength
                self.play_extra_data = play_extra_data

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerPlayToCampaignEvent:
                return Database.Player.PlayerPlayToCampaignEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event_id,
                    guild,
                    extra_data["player_id"],
                    extra_data["creature_id"],
                    extra_data["strength"],
                    extra_data["play_extra_data"],
                )

            def extra_data(self) -> str:
                return json.dumps(
                    {
                        "player_id": self.player_id,
                        "creature_id": self.creature_id,
                        "strength": self.strength,
                        "play_extra_data": self.play_extra_data,
                    }
                )

            def text(self) -> str:
                return f"<player:{self.player_id}> makes <creature:{self.creature_id}> campaign gaining {self.strength} {resource_to_emoji(Resource.STRENGTH)} Strength"

        class PlayerOrderRechargeEvent(Event):
            event_type = "player_order_recharge"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                player_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.player_id = player_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerOrderRechargeEvent:
                return Database.Player.PlayerOrderRechargeEvent(
                    parent, id, timestamp, parent_event_id, guild, extra_data["player_id"]
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
                        sub_con.add_event(
                            Database.Player.PlayerOrderRechargedEvent(
                                self.parent,
                                self.parent.fresh_event_id(self.guild, con=sub_con),
                                time.time(),
                                None,
                                self.guild,
                                self.player_id,
                            ),
                        )

                        player.gain([Gain(resource=Resource.ORDERS, amount=1)], con=sub_con)

                    if (
                        len(
                            player.test_recharges(con=con)[
                                Database.Player.PlayerOrderRechargeEvent.event_type
                            ]
                        )
                        == 1
                    ):
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

        class PlayerOrderRechargedEvent(PlayerOrderRechargeEvent):
            event_type = "player_order_recharged"

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerOrderRechargedEvent:
                return Database.Player.PlayerOrderRechargedEvent(
                    parent, id, timestamp, parent_event_id, guild, extra_data["player_id"]
                )

            def resolve(
                self,
                con: Optional[Database.TransactionManager] = None,
            ) -> None:
                pass

        class PlayerMagicRechargeEvent(Event):
            event_type = "player_magic_recharge"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                player_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.player_id = player_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerMagicRechargeEvent:
                return Database.Player.PlayerMagicRechargeEvent(
                    parent, id, timestamp, parent_event_id, guild, extra_data["player_id"]
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
                        sub_con.add_event(
                            Database.Player.PlayerMagicRechargedEvent(
                                self.parent,
                                self.parent.fresh_event_id(self.guild, con=sub_con),
                                time.time(),
                                None,
                                self.guild,
                                self.player_id,
                            ),
                        )

                        player.gain([Gain(resource=Resource.MAGIC, amount=1)], con=sub_con)

                    if (
                        len(
                            player.test_recharges(con=con)[
                                Database.Player.PlayerMagicRechargeEvent.event_type
                            ]
                        )
                        == 1
                    ):
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

        class PlayerMagicRechargedEvent(PlayerMagicRechargeEvent):
            event_type = "player_magic_recharged"

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerMagicRechargedEvent:
                return Database.Player.PlayerMagicRechargedEvent(
                    parent, id, timestamp, parent_event_id, guild, extra_data["player_id"]
                )

            def resolve(
                self,
                con: Optional[Database.TransactionManager] = None,
            ) -> None:
                pass

        class PlayerCardRechargeEvent(Event):
            event_type = "player_card_recharge"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                player_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.player_id = player_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerCardRechargeEvent:
                return Database.Player.PlayerCardRechargeEvent(
                    parent, id, timestamp, parent_event_id, guild, extra_data["player_id"]
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

                    if len(player.get_hand(con=sub_con)) < guild_config["max_cards"]:
                        sub_con.add_event(
                            Database.Player.PlayerCardRechargedEvent(
                                self.parent,
                                self.parent.fresh_event_id(self.guild, con=sub_con),
                                time.time(),
                                None,
                                self.guild,
                                self.player_id,
                            ),
                        )

                        player.draw_cards(1, con=sub_con)

                    if (
                        len(
                            player.test_recharges(con=con)[
                                Database.Player.PlayerCardRechargeEvent.event_type
                            ]
                        )
                        == 1
                    ):
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

        class PlayerCardRechargedEvent(PlayerCardRechargeEvent):
            event_type = "player_card_recharged"

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Player.PlayerCardRechargedEvent:
                return Database.Player.PlayerCardRechargedEvent(
                    parent, id, timestamp, parent_event_id, guild, extra_data["player_id"]
                )

            def resolve(
                self,
                con: Optional[Database.TransactionManager] = None,
            ) -> None:
                pass

    class BaseCreature:
        id = -1
        name = "default_creature"
        quest_region_categories: list[RegionCategory] = []
        claim_cost: int = 0
        related_creatures: List[Database.BaseCreature] = []

        def __init__(self: Database.BaseCreature):
            return

        def __repr__(self) -> str:
            return f"<BaseCreature: {self.name}>"

        def __eq__(self, other: Any) -> bool:
            if isinstance(other, Database.BaseCreature):
                return str(self) == str(other)
            return False

        def text(self) -> str:
            region_category_string = " ".join([r.emoji for r in self.quest_region_categories])
            return f"{region_category_string} {self.name.title()}"

        # questing
        def quest_ability_effect_short_text(self) -> str:
            return ""

        def quest_ability_effect_full_text(self) -> str:
            return ""

        def quest_ability_effect_price(
            self,
            region_db: Database.Region,
            creature_db: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
            extra_data: EXTRA_DATA = [],
        ) -> None:
            return

        def quest_ability_effect(
            self,
            region_db: Database.Region,
            creature_db: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
            extra_data: EXTRA_DATA = [],
        ) -> None:
            return

        # campaigning
        def campaign_ability_effect_short_text(self) -> str:
            return ""

        def campaign_ability_effect_full_text(self) -> str:
            return ""

        def campaign_ability_effect_price(
            self,
            creature_db: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
            extra_data: EXTRA_DATA = [],
        ) -> None:
            return

        def campaign_ability_effect(
            self,
            creature_db: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
            extra_data: EXTRA_DATA = [],
        ) -> int:
            return 0

        def campaign_recharge_effect(
            self, creature_db: Database.Creature, con: Optional[Database.TransactionManager] = None
        ) -> None:
            return

    class Creature:
        def __init__(
            self,
            parent: Database,
            id: int,
            creature: Database.BaseCreature,
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

        def text(self) -> str:
            return self.creature.text()

        def occupies(
            self, con: Optional[Database.TransactionManager] = None
        ) -> Optional[Tuple[Database.Region, int]]:
            assert False

        def change_strength(
            self, new_strength: int, con: Optional[Database.TransactionManager] = None
        ) -> None:
            assert False

        class CreatureRechargeEvent(Event):
            event_type = "creature_recharge"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                creature_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.creature_id = creature_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.Creature.CreatureRechargeEvent:
                return Database.Creature.CreatureRechargeEvent(
                    parent, id, timestamp, parent_event_id, guild, extra_data["creature_id"]
                )

            def extra_data(self) -> str:
                return json.dumps({"creature_id": self.creature_id})

            def text(self) -> str:
                return f"<creature:{self.creature_id}> has recharged"

            def resolve(
                self,
                con: Optional[Database.TransactionManager] = None,
            ) -> None:
                with self.parent.transaction(parent=con) as sub_con:
                    self.guild = cast(Database.Guild, self.guild)
                    creature = self.guild.get_creature(self.creature_id, con=sub_con)
                    if creature in [c for c, _ in creature.owner.get_played()]:
                        creature.owner.recharge_creature(creature, con=sub_con)
                        creature.creature.campaign_recharge_effect(creature, con=sub_con)

    class FreeCreature:
        def __init__(
            self,
            parent: Database,
            creature: Database.BaseCreature,
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

        def create_events(self, con: Optional[Database.TransactionManager] = None) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                sub_con.add_event(
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
                sub_con.add_event(
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

        def get_protected_timestamp(self, con: Optional[Database.TransactionManager] = None) -> int:
            return -1

        def get_expires_timestamp(self, con: Optional[Database.TransactionManager] = None) -> int:
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

        class FreeCreatureEvent(Event):
            event_type = "free_creature_base_event"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                channel_id: int,
                message_id: int,
            ):
                super().__init__(parent, id, timestamp, parent_event_id, guild)
                self.channel_id = channel_id
                self.message_id = message_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.FreeCreature.FreeCreatureEvent:
                assert False

            def extra_data(self) -> str:
                assert False

            def text(self) -> str:
                assert False

        class FreeCreatureProtectedEvent(FreeCreatureEvent):
            event_type = "free_creature_protected"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                channel_id: int,
                message_id: int,
            ):
                super().__init__(
                    parent, id, timestamp, parent_event_id, guild, channel_id, message_id
                )

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.FreeCreature.FreeCreatureProtectedEvent:
                return Database.FreeCreature.FreeCreatureProtectedEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event_id,
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

        class FreeCreatureExpiresEvent(FreeCreatureEvent):
            event_type = "free_creature_expires"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                channel_id: int,
                message_id: int,
            ):
                super().__init__(
                    parent, id, timestamp, parent_event_id, guild, channel_id, message_id
                )

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.FreeCreature.FreeCreatureExpiresEvent:
                return Database.FreeCreature.FreeCreatureExpiresEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event_id,
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

        class FreeCreatureClaimedEvent(FreeCreatureEvent):
            event_type = "free_creature_claimed"

            def __init__(
                self,
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                channel_id: int,
                message_id: int,
                player_id: int,
                creature_id: int,
            ):
                super().__init__(
                    parent, id, timestamp, parent_event_id, guild, channel_id, message_id
                )
                self.player_id = player_id
                self.creature_id = creature_id

            @staticmethod
            def from_extra_data(
                parent: Database,
                id: int,
                timestamp: float,
                parent_event_id: Optional[int],
                guild: Database.Guild,
                extra_data: dict[Any, Any],
            ) -> Database.FreeCreature.FreeCreatureClaimedEvent:
                return Database.FreeCreature.FreeCreatureClaimedEvent(
                    parent,
                    id,
                    timestamp,
                    parent_event_id,
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
                return f"<free_creature:({self.channel_id},{self.message_id})> has been claimed by <player:{self.player_id}>"


event_classes: list[type[Event]] = [
    Database.Guild.GuildCreatedEvent,
    Database.Guild.RegionAddedEvent,
    Database.Guild.RegionRemovedEvent,
    Database.Guild.PlayerAddedEvent,
    Database.Guild.PlayerRemovedEvent,
    Database.Guild.ConflictStartEvent,
    Database.Guild.ConflictEndEvent,
    Database.Guild.ConflictResultEvent,
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
    Database.Player.PlayerOrderRechargedEvent,
    Database.Player.PlayerMagicRechargeEvent,
    Database.Player.PlayerMagicRechargedEvent,
    Database.Player.PlayerCardRechargeEvent,
    Database.Player.PlayerCardRechargedEvent,
    Database.Player.PlayerDiscardCreatureEvent,
    Database.Player.PlayerDeleteCreatureEvent,
    Database.Player.PlayerCreateCreatureEvent,
    Database.Player.PlayerDrawCreatureEvent,
]
