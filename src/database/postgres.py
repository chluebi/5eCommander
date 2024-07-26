import random
import json
import time
from copy import deepcopy

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
)

from src.core.base_types import (
    Resource,
    BaseResources,
    BaseRegion,
    BaseCreature,
    StartCondition,
    Event,
)

from src.database.database import Database

from src.core.exceptions import (
    GuildNotFound,
    PlayerNotFound,
    CreatureNotFound,
    RegionNotFound,
    NotEnoughResourcesException,
    EmptyDeckException,
)

from src.core.regions import regions
from src.core.creatures import creatures


class PostgresDatabase(Database):

    def __init__(self, start_condition, engine: Engine):
        super().__init__(start_condition)
        self.engine = engine

        metadata = MetaData()

        guilds_table = Table(
            "guilds",
            metadata,
            Column("id", BigInteger, primary_key=True),
            Column("region_recharge", Integer, nullable=False, default=10),
            Column("creature_recharge", Integer, nullable=False, default=10),
            Column("free_protection", Integer, nullable=False, default=5),
            Column("free_expire", Integer, nullable=False, default=60),
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
            ForeignKeyConstraint(["guild_id", "roller_id"], ["players.guild_id", "players.id"]),
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

        metadata.create_all(self.engine)

    class TransactionManager(Database.TransactionManager):

        def __init__(self, parent, parent_manager):
            super().__init__(parent, parent_manager)

        def start_connection(self):
            parent: PostgresDatabase = self.parent
            con = parent.engine.connect()
            trans = con.begin()
            return con, trans

        def end_connection(self):
            self.con.close()

        def commit_transaction(self):
            self.trans.commit()

        def rollback_transaction(self):
            self.trans.rollback()

        def execute(self, *args):
            return self.con.execute(*args)

    def transaction(self, parent: TransactionManager = None):
        return self.TransactionManager(self, parent)

    # transaction stuff
    def start_connection(self):
        con = self.engine.connect()
        trans = con.begin()
        return con, trans

    def end_connection(self, con: Connection):
        con.close()

    def commit_transaction(self, trans: RootTransaction):
        trans.commit()

    def rollback_transaction(self, trans: RootTransaction):
        trans.rollback()

    def fresh_event_id(self, guild, con=None):
        with self.transaction(parent=con) as con:
            sql = text("SELECT COALESCE(MAX(id), -1) + 1 FROM events WHERE guild_id = :guild_id")
            result = con.execute(sql, {"guild_id": guild.id}).scalar() + (
                len(con.get_root().get_events()) if con else 0
            )
            return result

    def add_event(self, event: Event, con=None):
        with self.transaction(parent=con) as con:
            event_sql = text(
                "INSERT INTO events (id, guild_id, timestamp, parent_event_id, event_type, extra_data) VALUES (:id, :guild_id, :timestamp, :parent_event_id, :event_type, :extra_data)"
            )
            con.execute(
                event_sql,
                {
                    "id": event.id,
                    "guild_id": event.guild.id,
                    "timestamp": event.timestamp,
                    "parent_event_id": event.parent_event.id if event.parent_event else None,
                    "event_type": event.event_type,
                    "extra_data": event.extra_data(),
                },
            )

    def add_guild(self, guild_id: int, con=None) -> Database.Guild:

        guild = PostgresDatabase.Guild(self, guild_id)

        with self.transaction(parent=con) as con:
            sql_guild = text(
                """
                INSERT INTO guilds (id, region_recharge, creature_recharge, free_protection, free_expire)
                VALUES (:guild_id, 10, 10, 5, 60)
            """
            )
            con.execute(sql_guild, {"guild_id": guild_id})

            for base_region in self.start_condition.start_active_regions:
                guild.add_region(base_region, con=con)

            for base_creature in self.start_condition.start_available_creatures:
                guild.add_to_creature_pool(base_creature, con=con)

        return guild

    def get_guilds(self, con=None):
        with self.transaction(parent=con) as con:
            sql = text("SELECT id FROM guilds")
            result = con.execute(sql)
            guilds = [PostgresDatabase.Guild(self, row[0]) for row in result]
            return guilds

    def get_guild(self, guild_id: int, con=None) -> Database.Guild:
        with self.transaction(parent=con) as con:
            sql = text("SELECT id FROM guilds WHERE id = :id")
            result = con.execute(sql, {"id": guild_id}).fetchone()

            if not result:
                raise GuildNotFound("No guilds with this guild_id")

            guild = PostgresDatabase.Guild(self, result[0])

            return guild

    def remove_guild(self, guild: Database.Guild, con=None) -> Database.Guild:
        with self.transaction(parent=con) as con:
            sql = text("DELETE FROM guilds WHERE id = :guild_id")
            con.execute(sql, {"guild_id": guild.id})
            return guild

    class Guild(Database.Guild):

        def __init__(self, parent: Database, guild_id: int):
            super().__init__(parent, guild_id)

        def get_events(self, timestamp_start: int, timestamp_end: int, con=None) -> list[Event]:
            with self.parent.transaction(parent=con) as con:
                event_classes: list[type[Event]] = [
                    Database.Guild.RegionAddedEvent,
                    Database.Guild.RegionRemovedEvent,
                    Database.Guild.PlayerAddedEvent,
                    Database.Guild.PlayerRemovedEvent,
                    Database.Region.RegionRechargeEvent,
                    Database.Creature.CreatureRechargeEvent,
                    Database.FreeCreature.FreeCreatureProtectedEvent,
                    Database.FreeCreature.FreeCreatureExpiresEvent,
                ]

                sql = text(
                    f"""
                    SELECT * FROM events
                    WHERE guild_id = :guild_id
                    AND timestamp BETWEEN :start AND :end
                """
                )

                results = con.execute(
                    sql, {"guild_id": self.id, "start": timestamp_start, "end": timestamp_end}
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

        def set_config(self, config: dict, con=None) -> None:
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    """
                    UPDATE Guilds SET 
                        region_recharge = :region_recharge, 
                        creature_recharge = :creature_recharge, 
                        free_protection = :free_protection, 
                        free_expire = :free_expire 
                    WHERE guild_id = :guild_id
                """
                )
                con.execute(
                    sql,
                    {
                        "guild_id": self.id,
                        "region_recharge": config["region_recharge"],
                        "creature_recharge": config["creature_recharge"],
                        "free_protection": config["free_protection"],
                        "free_expire": config["free_expire"],
                    },
                )

        def get_config(self, con=None) -> dict:
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    "SELECT region_recharge, creature_recharge, free_protection, free_expire FROM guilds WHERE id = :guild_id"
                )
                result = con.execute(sql, {"guild_id": self.id}).fetchone()
                if result is not None:
                    config = {
                        "region_recharge": result[0],
                        "creature_recharge": result[1],
                        "free_protection": result[2],
                        "free_expire": result[3],
                    }
                return config

        def fresh_region_id(self, con=None) -> int:
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    "SELECT COALESCE(MAX(id), -1) + 1 AS next_id FROM regions WHERE guild_id = :guild_id"
                )
                result = con.execute(sql, {"guild_id": self.id}).scalar() + (
                    len(con.get_root().get_events()) if con else 0
                )
                return result

        def add_region(self, base_region: BaseRegion, con=None) -> Database.Region:
            with self.parent.transaction(parent=con) as con:
                super().add_region(base_region, con=con)

                region_id = self.fresh_region_id(con=con)
                sql = text(
                    """
                    INSERT INTO regions (id, guild_id, base_region_id)
                    VALUES (:id, :guild_id, :base_region_id)
                """
                )
                con.execute(
                    sql, {"id": region_id, "guild_id": self.id, "base_region_id": base_region.id}
                )

                event_id = self.parent.fresh_event_id(self, con=con)
                con.add_event(
                    Database.Guild.RegionAddedEvent(
                        self.parent, event_id, time.time(), None, self, region_id
                    ),
                )
                return PostgresDatabase.Region(self.parent, region_id, base_region, self)

        def get_regions(self, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text("SELECT id, base_region_id FROM regions WHERE guild_id = :guild_id")
                results = con.execute(sql, {"guild_id": self.id}).fetchall()
                return [
                    PostgresDatabase.Region(self.parent, row[0], regions[row[1]], self)
                    for row in results
                ]

        def get_region(self, region_id: int, con=None) -> Database.Region:
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    "SELECT id, base_region_id FROM regions WHERE id = :id AND guild_id = :guild_id"
                )
                result = con.execute(sql, {"id": region_id, "guild_id": self.id}).fetchone()
                if not result:
                    raise RegionNotFound("No regions with this id")
                return PostgresDatabase.Region(self.parent, result[0], regions[result[1]], self)

        def remove_region(self, region: Database.Region, con=None) -> Database.Region:
            with self.parent.transaction(parent=con) as con:
                super().remove_region(region, con=con)

                sql = text("DELETE FROM regions WHERE id = :id AND guild_id = :guild_id")
                con.execute(sql, {"id": region.id, "guild_id": self.id})

                event_id = self.parent.fresh_event_id(self, con=con)
                con.add_event(
                    Database.Guild.RegionRemovedEvent(
                        self.parent, event_id, time.time(), None, self, region.id
                    ),
                )
                return region

        def add_player(self, player_id: int, con=None) -> Database.Player:
            player = PostgresDatabase.Player(self.parent, player_id, self)

            with self.parent.transaction(parent=con) as con:
                sql_player = text(
                    "INSERT INTO players (id, guild_id) VALUES (:player_id, :guild_id)"
                )

                con.execute(sql_player, {"player_id": player_id, "guild_id": self.id})

                for base_creature in self.parent.start_condition.start_deck:
                    creature = self.add_creature(base_creature, player, con=con)
                    player.add_to_discard(creature, con=con)

                player.reshuffle_discard(con=con)

                for resource_type in BaseResources:
                    sql = text(
                        """
                        INSERT INTO Resources (player_id, guild_id, resource_type, quantity) VALUES (:player_id, :guild_id, :resource_type, :quantity)
                    """
                    )
                    con.execute(
                        sql,
                        {
                            "quantity": 0,
                            "player_id": player.id,
                            "guild_id": self.id,
                            "resource_type": resource_type.value,
                        },
                    )

                event_id = self.parent.fresh_event_id(self, con=con)
                con.add_event(
                    Database.Guild.PlayerAddedEvent(
                        self.parent, event_id, time.time(), None, self, player_id
                    ),
                )

            return player

        def get_players(self, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text("SELECT id FROM players WHERE guild_id = :guild_id")
                results = con.execute(sql, {"guild_id": self.id}).fetchall()
                return [PostgresDatabase.Player(self.parent, row[0], self) for row in results]

        def get_player(self, player_id: int, con=None) -> Database.Player:
            with self.parent.transaction(parent=con) as con:
                sql = text("SELECT id FROM players WHERE guild_id = :guild_id AND id = :player_id")
                result = con.execute(sql, {"guild_id": self.id, "player_id": player_id}).fetchone()
                if not result:
                    raise PlayerNotFound("No players with this player_id")
                return PostgresDatabase.Player(self.parent, result[0], self)

        def remove_player(self, player: Database.Player, con=None) -> Database.Player:
            with self.parent.transaction(parent=con) as con:
                super().remove_player(player, con=con)

                sql = text("DELETE FROM players WHERE guild_id = :guild_id AND id = :player_id")
                con.execute(sql, {"guild_id": self.id, "player_id": player.id})

                event_id = self.parent.fresh_event_id(self, con=con)
                con.add_event(
                    Database.Guild.PlayerRemovedEvent(
                        self.parent, event_id, time.time(), None, self, player.id
                    ),
                )
                return player

        def fresh_creature_id(self, con=None) -> int:
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    "SELECT COALESCE(MAX(id), -1) + 1 FROM creatures WHERE guild_id = :guild_id"
                )
                result = con.execute(sql, {"guild_id": self.id}).scalar() + (
                    len(con.get_root().get_events()) if con else 0
                )
                return result

        def add_creature(
            self, creature: BaseCreature, owner: Database.Player, con=None
        ) -> Database.Creature:
            with self.parent.transaction(parent=con) as con:
                creature_id = self.fresh_creature_id(con=con)
                sql = text(
                    """
                    INSERT INTO creatures (id, guild_id, base_creature_id, owner_id)
                    VALUES (:id, :guild_id, :base_creature_id, :owner_id)
                """
                )
                con.execute(
                    sql,
                    {
                        "id": creature_id,
                        "guild_id": self.id,
                        "base_creature_id": creature.id,
                        "owner_id": owner.id,
                    },
                )
                return PostgresDatabase.Creature(self.parent, creature_id, creature, self, owner)

        def get_creatures(self, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    "SELECT id, base_creature_id, owner_id FROM creatures WHERE guild_id = :guild_id"
                )
                results = con.execute(sql, {"guild_id": self.id}).fetchall()
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

        def get_creature(self, creature_id: int, con=None) -> Database.Creature:
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    "SELECT id, base_creature_id, owner_id FROM creatures WHERE id = :creature_id AND guild_id = :guild_id"
                )
                result = con.execute(
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

        def remove_creature(self, creature: Database.Creature, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text("DELETE FROM creatures WHERE id = :id AND guild_id = :guild_id")
                con.execute(sql, {"id": creature.id, "guild_id": self.id})
                return creature

        def add_to_creature_pool(self, base_creature: BaseCreature, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text("INSERT INTO base_creatures (id, guild_id) VALUES (:id, :guild_id)")
                con.execute(sql, {"id": base_creature.id, "guild_id": self.id})

        def get_creature_pool(self, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text("SELECT id FROM base_creatures WHERE guild_id = :guild_id")
                results = con.execute(sql, {"guild_id": self.id}).fetchall()
                return [creatures[result[0]] for result in results]

        def get_random_from_creature_pool(self, con=None) -> int:
            with self.parent.transaction(parent=con) as con:
                creature_pool = self.get_creature_pool()
                if not creature_pool:
                    raise ValueError("Creature pool is empty")
                return random.choice(creature_pool)

        def remove_from_creature_pool(self, base_creature: BaseCreature, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text("DELETE FROM base_creatures WHERE id = :id AND guild_id = :guild_id")
                con.execute(sql, {"id": base_creature.id, "guild_id": self.id})

        def add_free_creature(
            self,
            base_creature: BaseCreature,
            channel_id: int,
            message_id: int,
            roller: Database.Player,
            con=None,
        ) -> Database.FreeCreature:
            with self.parent.transaction(parent=con) as con:
                config = self.get_config(con=con)
                timestamp_protected = self.parent.timestamp_after(config["free_protection"])
                timestamp_expires = self.parent.timestamp_after(config["free_expire"])
                sql = text(
                    """
                    INSERT INTO free_creatures (base_creature_id, guild_id, channel_id, message_id, roller_id, timestamp_protected, timestamp_expires)
                    VALUES (:base_creature_id, :guild_id, :channel_id, :message_id, :roller_id, :timestamp_protected, :timestamp_expires)
                """
                )
                con.execute(
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

        def get_free_creatures(self, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    """
                    SELECT base_creature_id, channel_id, message_id, roller_id, timestamp_protected, timestamp_expires 
                    FROM free_creatures 
                    WHERE guild_id = :guild_id
                """
                )
                results = con.execute(sql, {"guild_id": self.id}).fetchall()
                return [
                    PostgresDatabase.FreeCreature(
                        self.parent, creatures[row[0]], self, row[1], row[2], row[3], row[4], row[5]
                    )
                    for row in results
                ]

        def get_free_creature(
            self, channel_id: int, message_id: int, con=None
        ) -> Database.FreeCreature:
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    """
                    SELECT base_creature_id, channel_id, message_id, roller_id, timestamp_protected, timestamp_expires 
                    FROM free_creatures 
                    WHERE guild_id = :guild_id 
                    AND channel_id = :channel_id 
                    AND message_id = :message_id
                """
                )
                result = con.execute(
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

        def remove_free_creature(self, creature: Database.FreeCreature, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    "DELETE FROM free_creatures WHERE guild_id = :guild_id AND channel_id = :channel_id AND message_id = :message_id"
                )
                con.execute(
                    sql,
                    {
                        "guild_id": self.id,
                        "channel_id": creature.channel_id,
                        "message_id": creature.message_id,
                    },
                )
                return creature

    class Region(Database.Region):

        def __init__(self, parent: Database, id: int, region: BaseRegion, guild: Database.Guild):
            super().__init__(parent, id, region, guild)

        def occupy(self, creature: Database.Creature, con=None):
            with self.parent.transaction(parent=con) as con:
                if self.is_occupied(con=con):
                    raise Exception("Trying to occupy an occupied region")

                until = self.parent.timestamp_after(
                    self.guild.get_config(con=con)["region_recharge"]
                )
                sql = text(
                    """
                    INSERT INTO occupies (guild_id, creature_id, region_id, timestamp_occupied)
                    VALUES (:guild_id, :creature_id, :region_id, :timestamp)
                """
                )
                con.execute(
                    sql,
                    {
                        "guild_id": self.guild.id,
                        "creature_id": creature.id,
                        "region_id": self.id,
                        "timestamp": until,
                    },
                )

                event_id = self.parent.fresh_event_id(self.guild, con=con)
                self.parent.add_event(
                    Database.Region.RegionRechargeEvent(
                        self.parent, event_id, until, None, self.guild, self.id
                    ),
                    con=con,
                )

        def unoccupy(self, current: int, con=None):
            with self.parent.transaction(parent=con) as con:
                occupant, until = self.occupied(con=con)
                if occupant is None:
                    raise Exception("Trying to unoccupy an already free region")
                if current < until:
                    raise Exception("Trying to unoccupy with too early timestamp")

                sql = text(
                    "DELETE FROM occupies WHERE guild_id = :guild_id AND region_id = :region_id"
                )
                con.execute(sql, {"guild_id": self.guild.id, "region_id": self.id})
                self.occupant = None

        def occupied(self, con=None) -> tuple[Database.Creature, int]:
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    """
                    SELECT c.id, c.base_creature_id, o.timestamp_occupied FROM occupies o
                    JOIN creatures c ON c.id = o.creature_id AND c.guild_id = o.guild_id
                    WHERE o.guild_id = :guild_id AND o.region_id = :region_id
                """
                )
                result = con.execute(
                    sql, {"guild_id": self.guild.id, "region_id": self.id}
                ).fetchone()
                if result is not None:
                    creature = PostgresDatabase.Creature(
                        self.parent, result[0], creatures[result[1]], self.guild, self
                    )
                    return (creature, result[2])
                return (None, None)

        def is_occupied(self, con=None) -> bool:
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    "SELECT COUNT(*) FROM occupies WHERE guild_id = :guild_id AND region_id = :region_id"
                )
                count = con.execute(sql, {"guild_id": self.guild.id, "region_id": self.id}).scalar()
                return count > 0

    class Player(Database.Player):
        def __init__(self, parent: Database, user_id: int, guild: Database.Guild):
            super().__init__(parent, user_id, guild)

        def get_resources(self, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    "SELECT resource_type, quantity FROM resources WHERE player_id = :player_id AND guild_id = :guild_id"
                )
                results = con.execute(
                    sql, {"player_id": self.id, "guild_id": self.guild.id}
                ).fetchall()
                return {Resource(result[0]): result[1] for result in results}

        def set_resources(self, resources: dict[Resource, int], con=None):
            with self.parent.transaction(parent=con) as con:
                for resource_type, quantity in resources.items():
                    sql = text(
                        """
                        UPDATE Resources SET quantity = :quantity 
                        WHERE player_id = :player_id AND guild_id = :guild_id AND resource_type = :resource_type
                    """
                    )
                    con.execute(
                        sql,
                        {
                            "quantity": quantity,
                            "player_id": self.id,
                            "guild_id": self.guild.id,
                            "resource_type": resource_type.value,
                        },
                    )

        def has(self, resource: Resource, amount: int, con=None) -> bool:
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    "SELECT quantity FROM resources WHERE player_id = :player_id AND guild_id = :guild_id AND resource_type = :resource_type"
                )
                result = con.execute(
                    sql,
                    {
                        "player_id": self.id,
                        "guild_id": self.guild.id,
                        "resource_type": resource.value,
                    },
                ).scalar()
                return result >= amount if result is not None else False

        def give(self, resource: Resource, amount: int, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    """
                    UPDATE Resources SET quantity = quantity + :amount 
                    WHERE player_id = :player_id AND guild_id = :guild_id AND resource_type = :resource_type
                """
                )
                con.execute(
                    sql,
                    {
                        "amount": amount,
                        "player_id": self.id,
                        "guild_id": self.guild.id,
                        "resource_type": resource.value,
                    },
                )

        def get_deck(self, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    """
                    SELECT d.creature_id, c.base_creature_id 
                    FROM deck d 
                    JOIN creatures c ON d.creature_id = c.id 
                    WHERE d.player_id = :player_id AND d.guild_id = :guild_id
                """
                )
                results = con.execute(
                    sql, {"player_id": self.id, "guild_id": self.guild.id}
                ).fetchall()
                return [
                    PostgresDatabase.Creature(
                        self.parent, result[0], creatures[result[1]], self.guild, self
                    )
                    for result in results
                ]

        def get_hand(self, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    """
                    SELECT h.creature_id, c.base_creature_id 
                    FROM hand h 
                    JOIN creatures c ON h.creature_id = c.id 
                    WHERE h.player_id = :player_id AND h.guild_id = :guild_id
                """
                )
                results = con.execute(
                    sql, {"player_id": self.id, "guild_id": self.guild.id}
                ).fetchall()
                return [
                    PostgresDatabase.Creature(
                        self.parent, result[0], creatures[result[1]], self.guild, self
                    )
                    for result in results
                ]

        def get_discard(self, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    """
                    SELECT d.creature_id, c.base_creature_id 
                    FROM discard d 
                    JOIN creatures c ON d.creature_id = c.id 
                    WHERE d.player_id = :player_id AND d.guild_id = :guild_id
                """
                )
                results = con.execute(
                    sql, {"player_id": self.id, "guild_id": self.guild.id}
                ).fetchall()
                return [
                    PostgresDatabase.Creature(
                        self.parent, result[0], creatures[result[1]], self.guild, self
                    )
                    for result in results
                ]

        def draw_card_raw(self, con=None):

            with self.parent.transaction(parent=con) as con:
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
                result = con.execute(
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
                con.execute(
                    sql,
                    {"player_id": self.id, "guild_id": self.guild.id, "creature_id": drawn_card.id},
                )

                sql = text(
                    """
                    INSERT INTO hand (player_id, guild_id, creature_id, position)
                    VALUES (:player_id, :guild_id, :creature_id, (SELECT COALESCE(MAX(position), -1) + 1 FROM hand WHERE player_id = :player_id AND guild_id = :guild_id))
                """
                )
                con.execute(
                    sql,
                    {"player_id": self.id, "guild_id": self.guild.id, "creature_id": drawn_card.id},
                )

            return drawn_card

        def reshuffle_discard(self, con=None):
            with self.parent.transaction(parent=con) as con:
                discard = self.get_discard(con=con)
                for creature in discard:
                    sql = text(
                        "DELETE FROM discard WHERE player_id = :player_id AND guild_id = :guild_id AND creature_id = :creature_id"
                    )
                    con.execute(
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
                    con.execute(
                        sql,
                        {
                            "player_id": self.id,
                            "guild_id": self.guild.id,
                            "creature_id": creature.id,
                        },
                    )

        def delete_creature_from_hand(self, creature: Database.Creature, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    "DELETE FROM hand WHERE player_id = :player_id AND guild_id = :guild_id AND creature_id = :creature_id"
                )
                con.execute(
                    sql,
                    {"player_id": self.id, "guild_id": self.guild.id, "creature_id": creature.id},
                )

        def play_creature(self, creature: Database.Creature, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    "DELETE FROM hand WHERE player_id = :player_id AND guild_id = :guild_id AND creature_id = :creature_id"
                )
                con.execute(
                    sql,
                    {"player_id": self.id, "guild_id": self.guild.id, "creature_id": creature.id},
                )
                sql = text(
                    "INSERT INTO discard (player_id, guild_id, creature_id) VALUES (:player_id, :guild_id, :creature_id)"
                )
                con.execute(
                    sql,
                    {"player_id": self.id, "guild_id": self.guild.id, "creature_id": creature.id},
                )

        def add_to_discard(self, creature: Database.Creature, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    "INSERT INTO discard (player_id, guild_id, creature_id) VALUES (:player_id, :guild_id, :creature_id)"
                )
                con.execute(
                    sql,
                    {"player_id": self.id, "guild_id": self.guild.id, "creature_id": creature.id},
                )

    class Creature(Database.Creature):

        def __init__(
            self,
            parent,
            id: int,
            creature: BaseCreature,
            guild: Database.Guild,
            owner: Database.Player,
        ):

            super().__init__(parent, id, creature, guild, owner)

    class FreeCreature(Database.FreeCreature):
        def __init__(
            self,
            parent,
            creature_id: int,
            guild,
            channel_id: int,
            message_id: int,
            roller_id,
            timestamp_protected: int,
            timestamp_expires: int,
        ):
            super().__init__(
                parent,
                creature_id,
                guild,
                channel_id,
                message_id,
                roller_id,
                timestamp_protected,
                timestamp_expires,
            )
            self.timestamp_protected = timestamp_protected
            self.timestamp_expires = timestamp_expires

        def get_protected_timestamp(self, con=None) -> int:
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    """
                    SELECT timestamp_protected FROM free_creatures
                    WHERE guild_id = :guild_id AND channel_id = :channel_id AND message_id = :message_id
                """
                )
                result = con.execute(
                    sql,
                    {
                        "guild_id": self.guild.id,
                        "channel_id": self.channel_id,
                        "message_id": self.message_id,
                    },
                ).scalar()
                return result

        def get_expires_timestamp(self, con=None) -> int:
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    """
                    SELECT timestamp_expires FROM free_creatures
                    WHERE guild_id = :guild_id AND channel_id = :channel_id AND message_id = :message_id
                """
                )
                result = con.execute(
                    sql,
                    {
                        "guild_id": self.guild.id,
                        "channel_id": self.channel_id,
                        "message_id": self.message_id,
                    },
                ).scalar()
                return result

        def claimed(self, con=None):
            with self.parent.transaction(parent=con) as con:
                sql = text(
                    """
                    DELETE FROM free_creatures
                    WHERE guild_id = :guild_id AND channel_id = :channel_id AND message_id = :message_id
                """
                )
                con.execute(
                    sql,
                    {
                        "guild_id": self.guild.id,
                        "channel_id": self.channel_id,
                        "message_id": self.message_id,
                    },
                )
