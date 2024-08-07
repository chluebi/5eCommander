import random
import json
import time
from copy import deepcopy
from typing import List, Tuple, Type, Optional, Union, Any, cast
from collections import defaultdict

from sqlalchemy import (
    RootTransaction,
    Transaction,
    Connection,
    Engine,
    text,
    TextClause,
    MetaData,
    Table,
    Column,
    Integer,
    BigInteger,
    JSON,
    String,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    UniqueConstraint,
)

from src.core.base_types import (
    Resource,
    BaseResources,
    Event,
)

from src.database.database import Database, event_classes

from src.core.exceptions import (
    GuildNotFound,
    PlayerNotFound,
    CreatureNotFound,
    RegionNotFound,
    NotEnoughResourcesException,
    EmptyDeckException,
)

from src.definitions.regions import regions
from src.definitions.creatures import creatures


class PostgresDatabase(Database):

    def __init__(self, start_condition: Database.StartCondition, engine: Engine):
        super().__init__(start_condition)
        self.engine = engine

        metadata = MetaData()

        guilds_table = Table(
            "guilds",
            metadata,
            Column("id", BigInteger, primary_key=True),
            Column("config", JSON, nullable=False),
        )

        events_table = Table(
            "events",
            metadata,
            Column("id", BigInteger, nullable=False),
            Column("guild_id", BigInteger, nullable=False),
            Column("timestamp", BigInteger, nullable=False),
            Column("parent_event_id", BigInteger, nullable=True),
            Column("event_type", String, nullable=False),
            Column("extra_data", JSON, nullable=True),
            # extra arguments for efficiency
            Column("region_id", BigInteger, nullable=True),
            Column("player_id", BigInteger, nullable=True),
            Column("creature_id", BigInteger, nullable=True),
            ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
            ForeignKeyConstraint(
                ["parent_event_id", "guild_id"],
                ["events.id", "events.guild_id"],
                ondelete="CASCADE",
            ),
            PrimaryKeyConstraint("id", "guild_id", name="pk_events"),
        )

        region_table = Table(
            "regions",
            metadata,
            Column("id", BigInteger, nullable=False),
            Column("guild_id", BigInteger, nullable=False),
            Column("base_region_id", BigInteger, nullable=False),
            ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
            PrimaryKeyConstraint("id", "guild_id", name="pk_regions"),
        )

        player_table = Table(
            "players",
            metadata,
            Column("id", BigInteger, nullable=False),
            Column("guild_id", BigInteger, nullable=False),
            ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
            PrimaryKeyConstraint("id", "guild_id", name="pk_players"),
        )

        base_creature_table = Table(
            "base_creatures",
            metadata,
            Column("id", BigInteger, nullable=False),
            Column("guild_id", BigInteger, nullable=False),
            ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
            PrimaryKeyConstraint("id", "guild_id", name="pk_base_creatures"),
        )

        creature_table = Table(
            "creatures",
            metadata,
            Column("id", BigInteger, nullable=False),
            Column("guild_id", BigInteger, nullable=False),
            Column("owner_id", BigInteger, nullable=False),
            Column("base_creature_id", BigInteger, nullable=False),
            ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
            ForeignKeyConstraint(
                ["guild_id", "owner_id"], ["players.guild_id", "players.id"], ondelete="CASCADE"
            ),
            ForeignKeyConstraint(
                ["guild_id", "base_creature_id"],
                ["base_creatures.guild_id", "base_creatures.id"],
                ondelete="CASCADE",
            ),
            PrimaryKeyConstraint("id", "guild_id", name="pk_creatures"),
        )

        occupies_table = Table(
            "occupies",
            metadata,
            Column("guild_id", BigInteger, nullable=False),
            Column("creature_id", BigInteger, nullable=False),
            Column("region_id", BigInteger, nullable=False),
            Column("timestamp_occupied", BigInteger, nullable=True),
            ForeignKeyConstraint(
                ["guild_id", "creature_id"],
                ["creatures.guild_id", "creatures.id"],
                ondelete="CASCADE",
            ),
            ForeignKeyConstraint(
                ["guild_id", "region_id"], ["regions.guild_id", "regions.id"], ondelete="CASCADE"
            ),
            PrimaryKeyConstraint("guild_id", "region_id", name="pk_occupies"),
        )

        free_creature_table = Table(
            "free_creatures",
            metadata,
            Column("base_creature_id", BigInteger, nullable=False),
            Column("guild_id", BigInteger, nullable=False),
            Column("channel_id", BigInteger, nullable=False),
            Column("message_id", BigInteger, nullable=False),
            Column("roller_id", BigInteger, nullable=False),
            Column("timestamp_protected", BigInteger, nullable=False),
            Column("timestamp_expires", BigInteger, nullable=False),
            ForeignKeyConstraint(
                ["guild_id", "base_creature_id"],
                ["base_creatures.guild_id", "base_creatures.id"],
                ondelete="CASCADE",
            ),
            ForeignKeyConstraint(
                ["guild_id", "roller_id"], ["players.guild_id", "players.id"], ondelete="CASCADE"
            ),
            PrimaryKeyConstraint("guild_id", "channel_id", "message_id", name="pk_free_creatures"),
        )

        resource_table = Table(
            "resources",
            metadata,
            Column("player_id", BigInteger, nullable=False),
            Column("guild_id", BigInteger, nullable=False),
            Column("resource_type", Integer, nullable=False),
            Column("quantity", Integer, nullable=False, default=0),
            ForeignKeyConstraint(
                ["guild_id", "player_id"], ["players.guild_id", "players.id"], ondelete="CASCADE"
            ),
            PrimaryKeyConstraint("player_id", "guild_id", "resource_type", name="pk_resources"),
        )

        deck_table = Table(
            "deck",
            metadata,
            Column("player_id", BigInteger, nullable=False),
            Column("guild_id", BigInteger, nullable=False),
            Column("creature_id", BigInteger, nullable=False),
            ForeignKeyConstraint(
                ["guild_id", "player_id"], ["players.guild_id", "players.id"], ondelete="CASCADE"
            ),
            ForeignKeyConstraint(
                ["guild_id", "creature_id"],
                ["creatures.guild_id", "creatures.id"],
                ondelete="CASCADE",
            ),
            PrimaryKeyConstraint("player_id", "guild_id", "creature_id", name="pk_deck"),
        )

        hand_table = Table(
            "hand",
            metadata,
            Column("player_id", BigInteger, nullable=False),
            Column("guild_id", BigInteger, nullable=False),
            Column("creature_id", BigInteger, nullable=False),
            Column("position", Integer, nullable=False),
            ForeignKeyConstraint(
                ["guild_id", "player_id"], ["players.guild_id", "players.id"], ondelete="CASCADE"
            ),
            ForeignKeyConstraint(
                ["guild_id", "creature_id"],
                ["creatures.guild_id", "creatures.id"],
                ondelete="CASCADE",
            ),
            PrimaryKeyConstraint("player_id", "guild_id", "creature_id", name="pk_hand"),
            UniqueConstraint("player_id", "guild_id", "position", name="uq_hand_position"),
        )

        discard_table = Table(
            "discard",
            metadata,
            Column("player_id", BigInteger, nullable=False),
            Column("guild_id", BigInteger, nullable=False),
            Column("creature_id", BigInteger, nullable=False),
            ForeignKeyConstraint(
                ["guild_id", "player_id"], ["players.guild_id", "players.id"], ondelete="CASCADE"
            ),
            ForeignKeyConstraint(
                ["guild_id", "creature_id"],
                ["creatures.guild_id", "creatures.id"],
                ondelete="CASCADE",
            ),
            PrimaryKeyConstraint("player_id", "guild_id", "creature_id", name="pk_discard"),
        )

        played_table = Table(
            "played",
            metadata,
            Column("player_id", BigInteger, nullable=False),
            Column("guild_id", BigInteger, nullable=False),
            Column("creature_id", BigInteger, nullable=False),
            Column("timestamp_recharge", BigInteger, nullable=False),
            ForeignKeyConstraint(
                ["guild_id", "player_id"], ["players.guild_id", "players.id"], ondelete="CASCADE"
            ),
            ForeignKeyConstraint(
                ["guild_id", "creature_id"],
                ["creatures.guild_id", "creatures.id"],
                ondelete="CASCADE",
            ),
            PrimaryKeyConstraint("player_id", "guild_id", "creature_id", name="pk_played"),
        )

        campaign_table = Table(
            "campaign",
            metadata,
            Column("player_id", BigInteger, nullable=False),
            Column("guild_id", BigInteger, nullable=False),
            Column("creature_id", BigInteger, nullable=False),
            Column("strength", BigInteger, nullable=False),
            ForeignKeyConstraint(
                ["guild_id", "player_id"], ["players.guild_id", "players.id"], ondelete="CASCADE"
            ),
            ForeignKeyConstraint(
                ["guild_id", "creature_id"],
                ["creatures.guild_id", "creatures.id"],
                ondelete="CASCADE",
            ),
            PrimaryKeyConstraint("player_id", "guild_id", "creature_id", name="pk_campaign"),
        )

        metadata.create_all(self.engine)

    class TransactionManager(Database.TransactionManager):

        def __init__(
            self,
            parent: Database,
            parent_manager: Optional[Database.TransactionManager],
        ):
            super().__init__(parent, parent_manager)

        def start_connection(self) -> Tuple[Connection, RootTransaction]:
            parent: PostgresDatabase = cast(PostgresDatabase, self.parent)
            con = parent.engine.connect()
            trans = con.begin()
            return con, trans

        def end_connection(self) -> None:
            self.con.close()

        def commit_transaction(self) -> None:
            self.trans.commit()

        def rollback_transaction(self) -> None:
            self.trans.rollback()

        def execute(self, *args: Any) -> Any:
            return self.con.execute(*args)

    def transaction(
        self, parent: Optional[Database.TransactionManager] = None
    ) -> Database.TransactionManager:
        return self.TransactionManager(self, parent)

    # transaction stuff
    def start_connection(self) -> Tuple[Connection, RootTransaction]:
        con = self.engine.connect()
        trans = con.begin()
        return con, trans

    def end_connection(self, con: Connection) -> None:
        con.close()

    def commit_transaction(self, trans: RootTransaction) -> None:
        trans.commit()

    def rollback_transaction(self, trans: RootTransaction) -> None:
        trans.rollback()

    def fresh_event_id(
        self,
        guild: Database.Guild,
        con: Optional[Database.TransactionManager] = None,
    ) -> int:
        with self.transaction(parent=con) as sub_con:
            sql = text("SELECT COALESCE(MAX(id), -1) + 1 FROM events WHERE guild_id = :guild_id")
            result = sub_con.execute(sql, {"guild_id": guild.id}).scalar() + (
                len(con.get_root().get_events()) if con else 0
            )
            return cast(int, result)

    def add_event(
        self,
        event: Event,
        con: Optional[Database.TransactionManager] = None,
    ) -> None:
        with self.transaction(parent=con) as sub_con:
            searched_dict: dict[str, Optional[int]] = defaultdict(None)
            searched_dict["region_id"] = None
            searched_dict["player_id"] = None
            searched_dict["creature_id"] = None

            for key, value in json.loads(event.extra_data()).items():
                for searched_key in searched_dict.keys():
                    if key == searched_key:
                        searched_dict[key] = value

            event_sql = text(
                "INSERT INTO events (id, guild_id, timestamp, parent_event_id, event_type, extra_data, region_id, player_id, creature_id) VALUES (:id, :guild_id, :timestamp, :parent_event_id, :event_type, :extra_data, :region_id, :player_id, :creature_id)"
            )
            sub_con.execute(
                event_sql,
                {
                    "id": event.id,
                    "guild_id": event.guild.id,
                    "timestamp": event.timestamp,
                    "parent_event_id": event.parent_event.id if event.parent_event else None,
                    "event_type": event.event_type,
                    "extra_data": event.extra_data(),
                    "region_id": searched_dict["region_id"],
                    "player_id": searched_dict["player_id"],
                    "creature_id": searched_dict["creature_id"],
                },
            )

    def get_event_by_id(
        self,
        event_id: int,
        con: Optional[Database.TransactionManager] = None,
    ) -> Event:
        with self.transaction(parent=con) as sub_con:

            sql = text(
                f"""
                        SELECT * FROM events WHERE id = :event_id
                    """
            )

            r = sub_con.execute(sql, {"event_id": event_id}).fetchone()

            event = None
            extra_data = r[5]

            for event_class in event_classes:

                if r[4] == event_class.event_type:
                    event = event_class.from_extra_data(
                        self, r[0], r[2], r[3], self.get_guild(r[1], con=sub_con), extra_data
                    )
                    break

            assert event is not None

            return event

    def add_guild(
        self,
        guild_id: int,
        con: Optional[Database.TransactionManager] = None,
    ) -> Database.Guild:

        guild = PostgresDatabase.Guild(self, guild_id)

        with self.transaction(parent=con) as sub_con:
            sql_guild = text(
                """
                INSERT INTO guilds (id, config)
                VALUES (:guild_id, :config)
            """
            )
            sub_con.execute(
                sql_guild,
                {"guild_id": guild_id, "config": json.dumps(self.start_condition.start_config)},
            )

            for base_region in self.start_condition.start_active_regions:
                guild.add_region(base_region, con=sub_con)

            for base_creature in self.start_condition.start_available_creatures:
                guild.add_to_creature_pool(base_creature, con=sub_con)

        return guild

    def get_guilds(self, con: Optional[Database.TransactionManager] = None) -> List[Database.Guild]:
        with self.transaction(parent=con) as sub_con:
            sql = text("SELECT id FROM guilds")
            result = sub_con.execute(sql)
            return [PostgresDatabase.Guild(self, row[0]) for row in result]

    def get_guild(
        self,
        guild_id: int,
        con: Optional[Database.TransactionManager] = None,
    ) -> Database.Guild:
        with self.transaction(parent=con) as sub_con:
            sql = text("SELECT id FROM guilds WHERE id = :id")
            result = sub_con.execute(sql, {"id": guild_id}).fetchone()

            if not result:
                raise GuildNotFound("No guilds with this guild_id")

            guild = PostgresDatabase.Guild(self, result[0])

            return guild

    def remove_guild(
        self,
        guild: Database.Guild,
        con: Optional[Database.TransactionManager] = None,
    ) -> Database.Guild:
        with self.transaction(parent=con) as sub_con:
            sql = text("DELETE FROM guilds WHERE id = :guild_id")
            sub_con.execute(sql, {"guild_id": guild.id})
            return guild

    class Guild(Database.Guild):

        def __init__(self, parent: Database, guild_id: int):
            super().__init__(parent, guild_id)

        def get_events(
            self,
            timestamp_start: float,
            timestamp_end: float,
            event_type: Optional[Type[Event]] = None,
            con: Optional[Database.TransactionManager] = None,
        ) -> list[Event]:
            with self.parent.transaction(parent=con) as sub_con:

                if event_type is None:
                    sql = text(
                        f"""
                        SELECT * FROM events
                        WHERE guild_id = :guild_id
                        AND timestamp BETWEEN :start AND :end
                        ORDER BY timestamp
                    """
                    )

                    results = sub_con.execute(
                        sql, {"guild_id": self.id, "start": timestamp_start, "end": timestamp_end}
                    ).fetchall()
                else:
                    sql = text(
                        f"""
                        SELECT * FROM events
                        WHERE guild_id = :guild_id
                        AND timestamp BETWEEN :start AND :end
                        AND event_type LIKE :event_type
                        ORDER BY timestamp
                    """
                    )

                    results = sub_con.execute(
                        sql,
                        {
                            "guild_id": self.id,
                            "start": timestamp_start,
                            "end": timestamp_end,
                            "event_type": event_type.event_type,
                        },
                    ).fetchall()

                events = []
                for r in results:
                    event = None
                    extra_data = r[5]

                    for event_class in event_classes:

                        if r[4] == event_class.event_type:
                            event = event_class.from_extra_data(
                                self.parent, r[0], r[2], r[3], self, extra_data
                            )
                            break

                    assert event is not None
                    events.append(event)

                return events

        def remove_event(
            self,
            event: Event,
            con: Optional[Database.TransactionManager] = None,
        ) -> Event:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text("DELETE FROM events WHERE id = :id AND guild_id = :guild_id")
                sub_con.execute(sql, {"id": event.id, "guild_id": self.id})

                return event

        def set_config(
            self,
            config: dict[Any, Any],
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    """
                    UPDATE Guilds SET config = :config 
                    WHERE guild_id = :guild_id
                """
                )
                sub_con.execute(
                    sql,
                    {"guild_id": self.id, "config": json.dumps(config)},
                )

        def get_config(self, con: Optional[Database.TransactionManager] = None) -> dict[Any, Any]:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text("SELECT config FROM guilds WHERE id = :guild_id")
                result = sub_con.execute(sql, {"guild_id": self.id}).fetchone()
                return cast(dict[Any, Any], result[0])

        def fresh_region_id(self, con: Optional[Database.TransactionManager] = None) -> int:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    "SELECT COALESCE(MAX(id), -1) + 1 AS next_id FROM regions WHERE guild_id = :guild_id"
                )
                result = sub_con.execute(sql, {"guild_id": self.id}).scalar() + (
                    len(con.get_root().get_events()) if con else 0
                )
                return cast(int, result)

        def add_region(
            self,
            base_region: Database.BaseRegion,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Region:
            with self.parent.transaction(parent=con) as sub_con:
                region_id = self.fresh_region_id(con=sub_con)
                sql = text(
                    """
                    INSERT INTO regions (id, guild_id, base_region_id)
                    VALUES (:id, :guild_id, :base_region_id)
                """
                )
                sub_con.execute(
                    sql, {"id": region_id, "guild_id": self.id, "base_region_id": base_region.id}
                )

                event_id = self.parent.fresh_event_id(self, con=sub_con)
                sub_con.add_event(
                    Database.Guild.RegionAddedEvent(
                        self.parent, event_id, time.time(), None, self, region_id
                    ),
                )
                return PostgresDatabase.Region(self.parent, region_id, base_region, self)

        def get_regions(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.Region]:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text("SELECT id, base_region_id FROM regions WHERE guild_id = :guild_id")
                results = sub_con.execute(sql, {"guild_id": self.id}).fetchall()
                return [
                    PostgresDatabase.Region(self.parent, row[0], regions[row[1]], self)
                    for row in results
                ]

        def get_region(
            self,
            region_id: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Region:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    "SELECT id, base_region_id FROM regions WHERE id = :id AND guild_id = :guild_id"
                )
                result = sub_con.execute(sql, {"id": region_id, "guild_id": self.id}).fetchone()
                if not result:
                    raise RegionNotFound("No regions with this id")
                return PostgresDatabase.Region(self.parent, result[0], regions[result[1]], self)

        def remove_region(
            self,
            region: Database.Region,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Region:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text("DELETE FROM regions WHERE id = :id AND guild_id = :guild_id")
                sub_con.execute(sql, {"id": region.id, "guild_id": self.id})

                event_id = self.parent.fresh_event_id(self, con=sub_con)
                sub_con.add_event(
                    Database.Guild.RegionRemovedEvent(
                        self.parent, event_id, time.time(), None, self, region.id
                    ),
                )
                return region

        def add_player(
            self,
            player_id: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Player:
            player = PostgresDatabase.Player(self.parent, player_id, self)
            guild_config = self.get_config()

            with self.parent.transaction(parent=con) as sub_con:
                sql_player = text(
                    "INSERT INTO players (id, guild_id) VALUES (:player_id, :guild_id)"
                )

                sub_con.execute(sql_player, {"player_id": player_id, "guild_id": self.id})

                for base_creature in self.parent.start_condition.start_deck:
                    creature = self.add_creature(base_creature, player, con=sub_con)
                    player.add_to_discard(creature, con=sub_con)

                player.reshuffle_discard(con=sub_con)

                for resource_type in BaseResources:
                    sql = text(
                        """
                        INSERT INTO Resources (player_id, guild_id, resource_type, quantity) VALUES (:player_id, :guild_id, :resource_type, :quantity)
                    """
                    )
                    sub_con.execute(
                        sql,
                        {
                            "quantity": 0,
                            "player_id": player.id,
                            "guild_id": self.id,
                            "resource_type": resource_type.value,
                        },
                    )

                # recharge events
                event_id = self.parent.fresh_event_id(self, con=sub_con)
                sub_con.add_event(
                    Database.Player.PlayerOrderRechargeEvent(
                        self.parent,
                        event_id,
                        time.time() + guild_config["order_recharge"],
                        None,
                        self,
                        player_id,
                    ),
                )
                event_id = self.parent.fresh_event_id(self, con=sub_con)
                sub_con.add_event(
                    Database.Player.PlayerMagicRechargeEvent(
                        self.parent,
                        event_id,
                        time.time() + guild_config["magic_recharge"],
                        None,
                        self,
                        player_id,
                    ),
                )
                event_id = self.parent.fresh_event_id(self, con=sub_con)
                sub_con.add_event(
                    Database.Player.PlayerCardRechargeEvent(
                        self.parent,
                        event_id,
                        time.time() + guild_config["card_recharge"],
                        None,
                        self,
                        player_id,
                    ),
                )
                # recharge events

                event_id = self.parent.fresh_event_id(self, con=sub_con)
                sub_con.add_event(
                    Database.Guild.PlayerAddedEvent(
                        self.parent, event_id, time.time(), None, self, player_id
                    ),
                )

            return player

        def get_players(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.Player]:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text("SELECT id FROM players WHERE guild_id = :guild_id")
                results = sub_con.execute(sql, {"guild_id": self.id}).fetchall()
                return [PostgresDatabase.Player(self.parent, row[0], self) for row in results]

        def get_player(
            self,
            player_id: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Player:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text("SELECT id FROM players WHERE guild_id = :guild_id AND id = :player_id")
                result = sub_con.execute(
                    sql, {"guild_id": self.id, "player_id": player_id}
                ).fetchone()
                if not result:
                    raise PlayerNotFound("No players with this player_id")
                return PostgresDatabase.Player(self.parent, result[0], self)

        def remove_player(
            self,
            player: Database.Player,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Player:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text("DELETE FROM players WHERE guild_id = :guild_id AND id = :player_id")
                sub_con.execute(sql, {"guild_id": self.id, "player_id": player.id})

                event_id = self.parent.fresh_event_id(self, con=sub_con)
                sub_con.add_event(
                    Database.Guild.PlayerRemovedEvent(
                        self.parent, event_id, time.time(), None, self, player.id
                    ),
                )
                return player

        def fresh_creature_id(self, con: Optional[Database.TransactionManager] = None) -> int:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    "SELECT COALESCE(MAX(id), -1) + 1 FROM creatures WHERE guild_id = :guild_id"
                )
                result = sub_con.execute(sql, {"guild_id": self.id}).scalar() + (
                    len(con.get_root().get_events()) if con else 0
                )
                return cast(int, result)

        def add_creature(
            self,
            creature: Database.BaseCreature,
            owner: Database.Player,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Creature:
            with self.parent.transaction(parent=con) as sub_con:
                creature_id = self.fresh_creature_id(con=sub_con)
                sql = text(
                    """
                    INSERT INTO creatures (id, guild_id, base_creature_id, owner_id)
                    VALUES (:id, :guild_id, :base_creature_id, :owner_id)
                """
                )
                sub_con.execute(
                    sql,
                    {
                        "id": creature_id,
                        "guild_id": self.id,
                        "base_creature_id": creature.id,
                        "owner_id": owner.id,
                    },
                )
                return PostgresDatabase.Creature(self.parent, creature_id, creature, self, owner)

        def get_creatures(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.Creature]:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    "SELECT id, base_creature_id, owner_id FROM creatures WHERE guild_id = :guild_id"
                )
                results = sub_con.execute(sql, {"guild_id": self.id}).fetchall()
                return [
                    PostgresDatabase.Creature(
                        self.parent,
                        row[0],
                        creatures[row[1]],
                        self,
                        PostgresDatabase.Player(self.parent, row[2], self),
                    )
                    for row in results
                ]

        def get_creature(
            self,
            creature_id: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Creature:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    "SELECT id, base_creature_id, owner_id FROM creatures WHERE id = :creature_id AND guild_id = :guild_id"
                )
                result = sub_con.execute(
                    sql, {"creature_id": creature_id, "guild_id": self.id}
                ).fetchone()
                if not result:
                    raise CreatureNotFound("No creatures with this id")
                return PostgresDatabase.Creature(
                    self.parent,
                    result[0],
                    creatures[result[1]],
                    self,
                    PostgresDatabase.Player(self.parent, result[2], self),
                )

        def remove_creature(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.Creature:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text("DELETE FROM creatures WHERE id = :id AND guild_id = :guild_id")
                sub_con.execute(sql, {"id": creature.id, "guild_id": self.id})
                return creature

        def add_to_creature_pool(
            self,
            base_creature: Database.BaseCreature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text("INSERT INTO base_creatures (id, guild_id) VALUES (:id, :guild_id)")
                sub_con.execute(sql, {"id": base_creature.id, "guild_id": self.id})

        def get_creature_pool(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.BaseCreature]:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text("SELECT id FROM base_creatures WHERE guild_id = :guild_id")
                results = sub_con.execute(sql, {"guild_id": self.id}).fetchall()
                return [creatures[result[0]] for result in results]

        def get_random_from_creature_pool(
            self, con: Optional[Database.TransactionManager] = None
        ) -> Database.BaseCreature:
            with self.parent.transaction(parent=con) as sub_con:
                creature_pool = self.get_creature_pool()
                if not creature_pool:
                    raise ValueError("Creature pool is empty")
                return random.choice(creature_pool)

        def remove_from_creature_pool(
            self,
            base_creature: Database.BaseCreature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text("DELETE FROM base_creatures WHERE id = :id AND guild_id = :guild_id")
                sub_con.execute(sql, {"id": base_creature.id, "guild_id": self.id})

        def add_free_creature(
            self,
            base_creature: Database.BaseCreature,
            channel_id: int,
            message_id: int,
            roller: Database.Player,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.FreeCreature:
            with self.parent.transaction(parent=con) as sub_con:
                config = self.get_config(con=sub_con)
                timestamp_protected = self.parent.timestamp_after(config["free_protection"])
                timestamp_expires = self.parent.timestamp_after(config["free_expire"])
                sql = text(
                    """
                    INSERT INTO free_creatures (base_creature_id, guild_id, channel_id, message_id, roller_id, timestamp_protected, timestamp_expires)
                    VALUES (:base_creature_id, :guild_id, :channel_id, :message_id, :roller_id, :timestamp_protected, :timestamp_expires)
                """
                )
                sub_con.execute(
                    sql,
                    {
                        "base_creature_id": base_creature.id,
                        "guild_id": self.id,
                        "channel_id": channel_id,
                        "message_id": message_id,
                        "roller_id": roller.id,
                        "timestamp_protected": timestamp_protected,
                        "timestamp_expires": timestamp_expires,
                    },
                )
                return PostgresDatabase.FreeCreature(
                    self.parent,
                    base_creature,
                    self,
                    channel_id,
                    message_id,
                    roller.id,
                    timestamp_protected,
                    timestamp_expires,
                )

        def get_free_creatures(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.FreeCreature]:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    """
                    SELECT base_creature_id, channel_id, message_id, roller_id, timestamp_protected, timestamp_expires 
                    FROM free_creatures 
                    WHERE guild_id = :guild_id
                """
                )
                results = sub_con.execute(sql, {"guild_id": self.id}).fetchall()
                return [
                    PostgresDatabase.FreeCreature(
                        self.parent, creatures[row[0]], self, row[1], row[2], row[3], row[4], row[5]
                    )
                    for row in results
                ]

        def get_free_creature(
            self,
            channel_id: int,
            message_id: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.FreeCreature:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    """
                    SELECT base_creature_id, channel_id, message_id, roller_id, timestamp_protected, timestamp_expires 
                    FROM free_creatures 
                    WHERE guild_id = :guild_id 
                    AND channel_id = :channel_id 
                    AND message_id = :message_id
                """
                )
                result = sub_con.execute(
                    sql, {"guild_id": self.id, "channel_id": channel_id, "message_id": message_id}
                ).fetchone()
                if not result:
                    raise CreatureNotFound("No creatures with this id")
                return PostgresDatabase.FreeCreature(
                    self.parent,
                    creatures[result[0]],
                    self,
                    result[1],
                    result[2],
                    result[3],
                    result[4],
                    result[5],
                )

        def remove_free_creature(
            self,
            creature: Database.FreeCreature,
            con: Optional[Database.TransactionManager] = None,
        ) -> Database.FreeCreature:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    "DELETE FROM free_creatures WHERE guild_id = :guild_id AND channel_id = :channel_id AND message_id = :message_id"
                )
                sub_con.execute(
                    sql,
                    {
                        "guild_id": self.id,
                        "channel_id": creature.channel_id,
                        "message_id": creature.message_id,
                    },
                )
                return creature

    class Region(Database.Region):

        def __init__(
            self, parent: Database, id: int, region: Database.BaseRegion, guild: Database.Guild
        ):
            super().__init__(parent, id, region, guild)

        def occupy(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                if self.is_occupied(con=sub_con):
                    raise Exception("Trying to occupy an occupied region")

                until = self.parent.timestamp_after(
                    self.guild.get_config(con=sub_con)["region_recharge"]
                )
                sql = text(
                    """
                    INSERT INTO occupies (guild_id, creature_id, region_id, timestamp_occupied)
                    VALUES (:guild_id, :creature_id, :region_id, :timestamp)
                """
                )
                sub_con.execute(
                    sql,
                    {
                        "guild_id": self.guild.id,
                        "creature_id": creature.id,
                        "region_id": self.id,
                        "timestamp": until,
                    },
                )

                event_id = self.parent.fresh_event_id(self.guild, con=sub_con)
                sub_con.add_event(
                    Database.Region.RegionRechargeEvent(
                        self.parent, event_id, until, None, self.guild, self.id
                    ),
                )

        def unoccupy(
            self,
            current: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                occupant, until = self.occupied(con=sub_con)
                if occupant is None or until is None:
                    raise Exception("Trying to unoccupy an already free region")
                if current < until:
                    raise Exception("Trying to unoccupy with too early timestamp")

                sql = text(
                    "DELETE FROM occupies WHERE guild_id = :guild_id AND region_id = :region_id"
                )
                sub_con.execute(sql, {"guild_id": self.guild.id, "region_id": self.id})
                self.occupant = None

        def occupied(
            self, con: Optional[Database.TransactionManager] = None
        ) -> tuple[Optional[Database.Creature], Optional[int]]:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    """
                    SELECT c.id, c.base_creature_id, o.timestamp_occupied FROM occupies o
                    JOIN creatures c ON c.id = o.creature_id AND c.guild_id = o.guild_id
                    WHERE o.guild_id = :guild_id AND o.region_id = :region_id
                """
                )
                result = sub_con.execute(
                    sql, {"guild_id": self.guild.id, "region_id": self.id}
                ).fetchone()
                if result is not None:
                    creature = self.guild.get_creature(result[0])
                    return (creature, result[2])
                return (None, None)

        def is_occupied(self, con: Optional[Database.TransactionManager] = None) -> bool:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    "SELECT COUNT(*) FROM occupies WHERE guild_id = :guild_id AND region_id = :region_id"
                )
                count = sub_con.execute(
                    sql, {"guild_id": self.guild.id, "region_id": self.id}
                ).scalar()
                return cast(bool, count > 0)

    class Player(Database.Player):
        def __init__(self, parent: Database, user_id: int, guild: Database.Guild):
            super().__init__(parent, user_id, guild)

        def get_resources(
            self, con: Optional[Database.TransactionManager] = None
        ) -> dict[Resource, int]:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    "SELECT resource_type, quantity FROM resources WHERE player_id = :player_id AND guild_id = :guild_id"
                )
                results = sub_con.execute(
                    sql, {"player_id": self.id, "guild_id": self.guild.id}
                ).fetchall()
                return {Resource(result[0]): result[1] for result in results}

        def set_resources(
            self,
            resources: dict[Resource, int],
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                for resource_type, quantity in resources.items():
                    sql = text(
                        """
                        UPDATE Resources SET quantity = :quantity 
                        WHERE player_id = :player_id AND guild_id = :guild_id AND resource_type = :resource_type
                    """
                    )
                    sub_con.execute(
                        sql,
                        {
                            "quantity": quantity,
                            "player_id": self.id,
                            "guild_id": self.guild.id,
                            "resource_type": resource_type.value,
                        },
                    )

        def has(
            self,
            resource: Resource,
            amount: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> bool:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    "SELECT quantity FROM resources WHERE player_id = :player_id AND guild_id = :guild_id AND resource_type = :resource_type"
                )
                result = sub_con.execute(
                    sql,
                    {
                        "player_id": self.id,
                        "guild_id": self.guild.id,
                        "resource_type": resource.value,
                    },
                ).scalar()
                return cast(bool, result >= amount) if result is not None else False

        def give(
            self,
            resource: Resource,
            amount: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
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
                        [(resource.value, amount)],
                    ),
                )

                sql = text(
                    """
                    UPDATE Resources SET quantity = quantity + :amount 
                    WHERE player_id = :player_id AND guild_id = :guild_id AND resource_type = :resource_type
                """
                )
                sub_con.execute(
                    sql,
                    {
                        "amount": amount,
                        "player_id": self.id,
                        "guild_id": self.guild.id,
                        "resource_type": resource.value,
                    },
                )

        def get_deck(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.Creature]:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    """
                    SELECT d.creature_id, c.base_creature_id 
                    FROM deck d 
                    JOIN creatures c ON d.creature_id = c.id 
                    WHERE d.player_id = :player_id AND d.guild_id = :guild_id
                """
                )
                results = sub_con.execute(
                    sql, {"player_id": self.id, "guild_id": self.guild.id}
                ).fetchall()
                return [
                    PostgresDatabase.Creature(
                        self.parent, result[0], creatures[result[1]], self.guild, self
                    )
                    for result in results
                ]

        def get_hand(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.Creature]:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    """
                    SELECT h.creature_id, c.base_creature_id 
                    FROM hand h 
                    JOIN creatures c ON h.creature_id = c.id 
                    WHERE h.player_id = :player_id AND h.guild_id = :guild_id
                """
                )
                results = sub_con.execute(
                    sql, {"player_id": self.id, "guild_id": self.guild.id}
                ).fetchall()
                return [
                    PostgresDatabase.Creature(
                        self.parent, result[0], creatures[result[1]], self.guild, self
                    )
                    for result in results
                ]

        def get_discard(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Database.Creature]:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    """
                    SELECT d.creature_id, c.base_creature_id 
                    FROM discard d 
                    JOIN creatures c ON d.creature_id = c.id 
                    WHERE d.player_id = :player_id AND d.guild_id = :guild_id
                """
                )
                results = sub_con.execute(
                    sql, {"player_id": self.id, "guild_id": self.guild.id}
                ).fetchall()
                return [
                    PostgresDatabase.Creature(
                        self.parent, result[0], creatures[result[1]], self.guild, self
                    )
                    for result in results
                ]

        def get_played(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Tuple[Database.Creature, int]]:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    """
                    SELECT p.creature_id, c.base_creature_id, p.timestamp_recharge 
                    FROM played p 
                    JOIN creatures c ON p.creature_id = c.id 
                    WHERE p.player_id = :player_id AND p.guild_id = :guild_id
                """
                )
                results = sub_con.execute(
                    sql, {"player_id": self.id, "guild_id": self.guild.id}
                ).fetchall()
                return [
                    (
                        PostgresDatabase.Creature(
                            self.parent, result[0], creatures[result[1]], self.guild, self
                        ),
                        cast(int, result[2]),
                    )
                    for result in results
                ]

        def get_campaign(
            self, con: Optional[Database.TransactionManager] = None
        ) -> List[Tuple[Database.Creature, int]]:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    """
                    SELECT ca.creature_id, c.base_creature_id, ca.strength 
                    FROM campaign ca 
                    JOIN creatures c ON ca.creature_id = c.id 
                    WHERE ca.player_id = :player_id AND ca.guild_id = :guild_id
                """
                )
                results = sub_con.execute(
                    sql, {"player_id": self.id, "guild_id": self.guild.id}
                ).fetchall()
                return [
                    (
                        PostgresDatabase.Creature(
                            self.parent, result[0], creatures[result[1]], self.guild, self
                        ),
                        cast(int, result[2]),
                    )
                    for result in results
                ]

        def get_events(
            self,
            timestamp_start: float,
            timestamp_end: float,
            event_type: Optional[Type[Event]] = None,
            con: Optional[Database.TransactionManager] = None,
        ) -> list[Event]:
            with self.parent.transaction(parent=con) as sub_con:

                if event_type is None:
                    sql = text(
                        f"""
                        SELECT * FROM events
                        WHERE guild_id = :guild_id
                        AND timestamp BETWEEN :start AND :end
                        AND player_id = :player_id
                        ORDER BY timestamp
                    """
                    )

                    results = sub_con.execute(
                        sql,
                        {
                            "guild_id": self.guild.id,
                            "start": timestamp_start,
                            "end": timestamp_end,
                            "player_id": self.id,
                        },
                    ).fetchall()
                else:
                    sql = text(
                        f"""
                        SELECT * FROM events
                        WHERE guild_id = :guild_id
                        AND timestamp BETWEEN :start AND :end
                        AND player_id = :player_id
                        AND event_type LIKE :event_type
                        ORDER BY timestamp
                    """
                    )

                    results = sub_con.execute(
                        sql,
                        {
                            "guild_id": self.guild.id,
                            "start": timestamp_start,
                            "end": timestamp_end,
                            "player_id": self.id,
                            "event_type": event_type.event_type,
                        },
                    ).fetchall()

                events = []
                for r in results:
                    event = None
                    extra_data = r[5]
                    assert extra_data["player_id"] == self.id

                    for event_class in event_classes:

                        if r[4] == event_class.event_type:
                            event = event_class.from_extra_data(
                                self.parent, r[0], r[2], r[3], self.guild, extra_data
                            )
                            break

                    assert event is not None
                    events.append(event)

                return events

        def draw_card_raw(
            self, con: Optional[Database.TransactionManager] = None
        ) -> Database.Creature:

            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    """
                    SELECT d.creature_id, c.base_creature_id 
                    FROM deck d
                    JOIN creatures c ON d.creature_id = c.id
                    WHERE d.player_id = :player_id AND d.guild_id = :guild_id 
                    ORDER BY RANDOM() 
                    LIMIT 1
                """
                )
                result = sub_con.execute(
                    sql, {"player_id": self.id, "guild_id": self.guild.id}
                ).fetchone()

                if not result:
                    raise EmptyDeckException()

                drawn_card = PostgresDatabase.Creature(
                    self.parent, result[0], creatures[result[1]], self.guild, self
                )

                sql = text(
                    """
                    DELETE FROM deck 
                    WHERE player_id = :player_id AND guild_id = :guild_id AND creature_id = :creature_id
                """
                )
                sub_con.execute(
                    sql,
                    {"player_id": self.id, "guild_id": self.guild.id, "creature_id": drawn_card.id},
                )

                sql = text(
                    """
                    INSERT INTO hand (player_id, guild_id, creature_id, position)
                    VALUES (:player_id, :guild_id, :creature_id, (SELECT COALESCE(MAX(position), -1) + 1 FROM hand WHERE player_id = :player_id AND guild_id = :guild_id))
                """
                )
                sub_con.execute(
                    sql,
                    {"player_id": self.id, "guild_id": self.guild.id, "creature_id": drawn_card.id},
                )

            return drawn_card

        def reshuffle_discard(self, con: Optional[Database.TransactionManager] = None) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                discard = self.get_discard(con=sub_con)
                for creature in discard:
                    sql = text(
                        "DELETE FROM discard WHERE player_id = :player_id AND guild_id = :guild_id AND creature_id = :creature_id"
                    )
                    sub_con.execute(
                        sql,
                        {
                            "player_id": self.id,
                            "guild_id": self.guild.id,
                            "creature_id": creature.id,
                        },
                    )
                    sql = text(
                        "INSERT INTO deck (player_id, guild_id, creature_id) VALUES (:player_id, :guild_id, :creature_id)"
                    )
                    sub_con.execute(
                        sql,
                        {
                            "player_id": self.id,
                            "guild_id": self.guild.id,
                            "creature_id": creature.id,
                        },
                    )

        def delete_creature_from_hand(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    "DELETE FROM hand WHERE player_id = :player_id AND guild_id = :guild_id AND creature_id = :creature_id"
                )
                sub_con.execute(
                    sql,
                    {"player_id": self.id, "guild_id": self.guild.id, "creature_id": creature.id},
                )

        def recharge_creature(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    "DELETE FROM played WHERE player_id = :player_id AND guild_id = :guild_id AND creature_id = :creature_id"
                )
                sub_con.execute(
                    sql,
                    {"player_id": self.id, "guild_id": self.guild.id, "creature_id": creature.id},
                )
                sql = text(
                    "INSERT INTO discard (player_id, guild_id, creature_id) VALUES (:player_id, :guild_id, :creature_id)"
                )
                sub_con.execute(
                    sql,
                    {"player_id": self.id, "guild_id": self.guild.id, "creature_id": creature.id},
                )

        def discard_creature_from_hand(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    "DELETE FROM hand WHERE player_id = :player_id AND guild_id = :guild_id AND creature_id = :creature_id"
                )
                sub_con.execute(
                    sql,
                    {"player_id": self.id, "guild_id": self.guild.id, "creature_id": creature.id},
                )
                sql = text(
                    "INSERT INTO discard (player_id, guild_id, creature_id) VALUES (:player_id, :guild_id, :creature_id)"
                )
                sub_con.execute(
                    sql,
                    {"player_id": self.id, "guild_id": self.guild.id, "creature_id": creature.id},
                )

        def play_creature(
            self,
            creature: Database.Creature,
            until: float,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    "DELETE FROM hand WHERE player_id = :player_id AND guild_id = :guild_id AND creature_id = :creature_id"
                )
                sub_con.execute(
                    sql,
                    {"player_id": self.id, "guild_id": self.guild.id, "creature_id": creature.id},
                )
                sql = text(
                    "INSERT INTO played (player_id, guild_id, creature_id, timestamp_recharge) VALUES (:player_id, :guild_id, :creature_id, :timestamp_recharge)"
                )
                sub_con.execute(
                    sql,
                    {
                        "player_id": self.id,
                        "guild_id": self.guild.id,
                        "creature_id": creature.id,
                        "timestamp_recharge": until,
                    },
                )

        def campaign_creature(
            self,
            creature: Database.Creature,
            strength: int,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    "DELETE FROM hand WHERE player_id = :player_id AND guild_id = :guild_id AND creature_id = :creature_id"
                )
                sub_con.execute(
                    sql,
                    {"player_id": self.id, "guild_id": self.guild.id, "creature_id": creature.id},
                )
                sql = text(
                    "INSERT INTO campaign (player_id, guild_id, creature_id, strength) VALUES (:player_id, :guild_id, :creature_id, :strength)"
                )
                sub_con.execute(
                    sql,
                    {
                        "player_id": self.id,
                        "guild_id": self.guild.id,
                        "creature_id": creature.id,
                        "strength": strength,
                    },
                )

        def add_to_discard(
            self,
            creature: Database.Creature,
            con: Optional[Database.TransactionManager] = None,
        ) -> None:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    "INSERT INTO discard (player_id, guild_id, creature_id) VALUES (:player_id, :guild_id, :creature_id)"
                )
                sub_con.execute(
                    sql,
                    {"player_id": self.id, "guild_id": self.guild.id, "creature_id": creature.id},
                )

    class Creature(Database.Creature):

        def __init__(
            self,
            parent: Database,
            id: int,
            creature: Database.BaseCreature,
            guild: Database.Guild,
            owner: Database.Player,
        ):

            super().__init__(parent, id, creature, guild, owner)

    class FreeCreature(Database.FreeCreature):
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
            super().__init__(
                parent,
                creature,
                guild,
                channel_id,
                message_id,
                roller_id,
                timestamp_protected,
                timestamp_expires,
            )
            self.timestamp_protected = timestamp_protected
            self.timestamp_expires = timestamp_expires

        def get_protected_timestamp(self, con: Optional[Database.TransactionManager] = None) -> int:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    """
                    SELECT timestamp_protected FROM free_creatures
                    WHERE guild_id = :guild_id AND channel_id = :channel_id AND message_id = :message_id
                """
                )
                result = sub_con.execute(
                    sql,
                    {
                        "guild_id": self.guild.id,
                        "channel_id": self.channel_id,
                        "message_id": self.message_id,
                    },
                ).scalar()
                return cast(int, result)

        def get_expires_timestamp(self, con: Optional[Database.TransactionManager] = None) -> int:
            with self.parent.transaction(parent=con) as sub_con:
                sql = text(
                    """
                    SELECT timestamp_expires FROM free_creatures
                    WHERE guild_id = :guild_id AND channel_id = :channel_id AND message_id = :message_id
                """
                )
                result = sub_con.execute(
                    sql,
                    {
                        "guild_id": self.guild.id,
                        "channel_id": self.channel_id,
                        "message_id": self.message_id,
                    },
                ).scalar()
                return cast(int, result)
