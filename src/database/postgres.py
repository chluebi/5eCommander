import random
from copy import deepcopy

from sqlalchemy import Engine, text, MetaData, Table, Column, Integer, ForeignKeyConstraint, PrimaryKeyConstraint, BigInteger

from src.core.base_types import (
    Resource,
    BaseResources,
    BaseRegion,
    BaseCreature,
    StartCondition,
    Event,
    Database,
)
from src.core.base_types import (
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

        # Continue using the previous metadata object
        metadata = MetaData()

        guilds_table = Table('Guilds', metadata,
            Column('id', BigInteger, primary_key=True),
            Column('region_recharge', Integer, nullable=False, default=10),
            Column('creature_recharge', Integer, nullable=False, default=10),
            Column('free_protection', Integer, nullable=False, default=5),
            Column('free_expire', Integer, nullable=False, default=60)
        )

        region_recharge_event_table = Table('RegionRechargeEvents', metadata,
            Column('id', BigInteger, nullable=False),
            Column('guild_id', BigInteger, nullable=False),
            Column('timestamp', BigInteger, nullable=False),
            Column('region_id', BigInteger, nullable=False),
            ForeignKeyConstraint(['guild_id'], ['Guilds.id']),
            PrimaryKeyConstraint('id', 'guild_id', name='pk_RegionRechargeEvents')
        )

        creature_recharge_event_table = Table('CreatureRechargeEvents', metadata,
            Column('id', BigInteger, nullable=False),
            Column('guild_id', BigInteger, nullable=False),
            Column('timestamp', BigInteger, nullable=False),
            Column('creature_id', BigInteger, nullable=False),
            ForeignKeyConstraint(['guild_id'], ['Guilds.id']),
            PrimaryKeyConstraint('id', 'guild_id', name='pk_CreatureRechargeEvents')
        )

        free_creature_protected_event_table = Table('FreeCreatureProtectedEvents', metadata,
            Column('id', BigInteger, nullable=False),
            Column('guild_id', BigInteger, nullable=False),
            Column('timestamp', BigInteger, nullable=False),
            Column('free_creature_id', BigInteger, nullable=False),
            ForeignKeyConstraint(['guild_id'], ['Guilds.id']),
            PrimaryKeyConstraint('id', 'guild_id', name='pk_FreeCreatureProtectedEvents')
        )

        free_creature_expires_event_table = Table('FreeCreatureExpiresEvents', metadata,
            Column('id', BigInteger, nullable=False),
            Column('guild_id', BigInteger, nullable=False),
            Column('timestamp', BigInteger, nullable=False),
            Column('free_creature_id', BigInteger, nullable=False),
            ForeignKeyConstraint(['guild_id'], ['Guilds.id']),
            PrimaryKeyConstraint('id', 'guild_id', name='pk_FreeCreatureExpiresEvents')
        )

        region_table = Table('Regions', metadata,
            Column('id', BigInteger, nullable=False),
            Column('guild_id', BigInteger, nullable=False),
            Column('base_region_id', BigInteger, nullable=False),
            ForeignKeyConstraint(['guild_id'], ['Guilds.id']),
            PrimaryKeyConstraint('id', 'guild_id', name='pk_Regions')
        )

        player_table = Table('Players', metadata,
            Column('id', BigInteger, nullable=False),
            Column('guild_id', BigInteger, nullable=False),
            ForeignKeyConstraint(['guild_id'], ['Guilds.id']),
            PrimaryKeyConstraint('id', 'guild_id', name='pk_Players')
        )

        base_creature_table = Table('BaseCreatures', metadata,
            Column('id', BigInteger, nullable=False),
            Column('guild_id', BigInteger, nullable=False),
            ForeignKeyConstraint(['guild_id'], ['Guilds.id']),
            PrimaryKeyConstraint('id', 'guild_id', name='pk_BaseCreatures')
        )

        creature_table = Table('Creatures', metadata,
            Column('id', BigInteger, nullable=False),
            Column('guild_id', BigInteger, nullable=False),
            Column('owner_id', BigInteger, nullable=False),
            Column('base_creature_id', BigInteger, nullable=False),
            ForeignKeyConstraint(['guild_id'], ['Guilds.id']),
            ForeignKeyConstraint(['guild_id', 'owner_id'], ['Players.guild_id', 'Players.id']),
            ForeignKeyConstraint(['guild_id', 'base_creature_id'], ['BaseCreatures.guild_id', 'BaseCreatures.id']),
            PrimaryKeyConstraint('id', 'guild_id', name='pk_Creatures')
        )

        occupies_table = Table('Occupies', metadata,
            Column('guild_id', BigInteger, nullable=False),
            Column('creature_id', BigInteger, nullable=False),
            Column('region_id', BigInteger, nullable=False),
            Column('timestamp_occupied', BigInteger, nullable=True),
            ForeignKeyConstraint(['guild_id', 'creature_id'], ['Creatures.guild_id', 'Creatures.id']),
            ForeignKeyConstraint(['guild_id', 'region_id'], ['Regions.guild_id', 'Regions.id']),
            PrimaryKeyConstraint('guild_id', 'region_id', name='pk_Occupies')
        )

        free_creature_table = Table('FreeCreatures', metadata,
            Column('base_creature_id', BigInteger, nullable=False),
            Column('guild_id', BigInteger, nullable=False),
            Column('channel_id', BigInteger, nullable=False),
            Column('message_id', BigInteger, nullable=False),
            Column('roller_id', BigInteger, nullable=False),
            Column('timestamp_protected', BigInteger, nullable=False),
            Column('timestamp_expires', BigInteger, nullable=False),
            ForeignKeyConstraint(['guild_id', 'base_creature_id'], ['BaseCreatures.guild_id', 'BaseCreatures.id']),
            ForeignKeyConstraint(['guild_id', 'roller_id'], ['Players.guild_id', 'Players.id']),
            PrimaryKeyConstraint('guild_id', 'channel_id', 'message_id', name='pk_FreeCreatures')
        )

        resource_table = Table('Resources', metadata,
            Column('player_id', BigInteger, nullable=False),
            Column('guild_id', BigInteger, nullable=False),
            Column('resource_type', Integer, nullable=False),
            Column('quantity', Integer, nullable=False, default=0),
            ForeignKeyConstraint(['guild_id', 'player_id'], ['Players.guild_id', 'Players.id']),
            PrimaryKeyConstraint('player_id', 'guild_id', 'resource_type', name='pk_Resources')
        )


        deck_table = Table('Deck', metadata,
            Column('player_id', BigInteger, nullable=False),
            Column('guild_id', BigInteger, nullable=False),
            Column('creature_id', BigInteger, nullable=False),
            ForeignKeyConstraint(['guild_id', 'player_id'], ['Players.guild_id', 'Players.id']),
            ForeignKeyConstraint(['guild_id', 'creature_id'], ['Creatures.guild_id', 'Creatures.id']),
            PrimaryKeyConstraint('player_id', 'guild_id', 'creature_id', name='pk_Deck')
        )

        hand_table = Table('Hand', metadata,
            Column('player_id', BigInteger, nullable=False),
            Column('guild_id', BigInteger, nullable=False),
            Column('creature_id', BigInteger, nullable=False),
            Column('order', Integer, nullable=False),
            ForeignKeyConstraint(['guild_id', 'player_id'], ['Players.guild_id', 'Players.id']),
            ForeignKeyConstraint(['guild_id', 'creature_id'], ['Creatures.guild_id', 'Creatures.id']),
            PrimaryKeyConstraint('player_id', 'guild_id', 'creature_id', name='pk_Hand')
        )

        discard_table = Table('Discard', metadata,
            Column('player_id', BigInteger, nullable=False),
            Column('guild_id', BigInteger, nullable=False),
            Column('creature_id', BigInteger, nullable=False),
            ForeignKeyConstraint(['guild_id', 'player_id'], ['Players.guild_id', 'Players.id']),
            ForeignKeyConstraint(['guild_id', 'creature_id'], ['Creatures.guild_id', 'Creatures.id']),
            PrimaryKeyConstraint('player_id', 'guild_id', 'creature_id', name='pk_Discard')
        )


        metadata.create_all(engine)

    # transaction stuff
    def start_transaction(self):
        if not self._in_transaction:
            self.engine.begin()
            self._in_transaction = True

    def end_transaction(self):
        if self._in_transaction:
            self.engine.commit()
            self._in_transaction = False

    def rollback_transaction(self):
        if self._in_transaction:
            self.engine.rollback()
            self._in_transaction = False

    def fresh_event_id(self, guild):
        sql = text("SELECT COALESCE(MAX(id), -1) + 1 FROM Events WHERE guild_id = :guild_id")
        result = self.engine.execute(sql, {'guild_id': guild}).scalar()
        return result

    def add_event(self, event: Event):
        if isinstance(event, Database.Region.RegionRechargeEvent):
            sql = text("INSERT INTO RegionRechargeEvents (id, guild_id, timestamp, region_id) VALUES (:id, :guild_id, :timestamp, :region_id)")
            self.engine.execute(sql, {'id': event.id, 'guild_id': event.guild.id, 'timestamp': event.timestamp, 'region_id': event.region.id})
        elif isinstance(event, Database.Creature.CreatureRechargeEvent):
            sql = text("INSERT INTO CreatureRechargeEvents (id, guild_id, timestamp, creature_id) VALUES (:id, :guild_id, :timestamp, :creature_id)")
            self.engine.execute(sql, {'id': event.id, 'guild_id': event.guild.id, 'timestamp': event.timestamp, 'creature_id': event.creature.id})
        elif isinstance(event, Database.FreeCreature.FreeCreatureProtectedEvent):
            sql = text("INSERT INTO FreeCreatureProtectedEvents (id, guild_id, timestamp, free_creature_id) VALUES (:id, :guild_id, :timestamp, :free_creature_id)")
            self.engine.execute(sql, {'id': event.id, 'guild_id': event.guild.id, 'timestamp': event.timestamp, 'free_creature_id': event.free_creature.id})
        elif isinstance(event, Database.FreeCreature.FreeCreatureExpiresEvent):
            sql = text("INSERT INTO FreeCreatureExpiresEvents (id, guild_id, timestamp, free_creature_id) VALUES (:id, :guild_id, :timestamp, :free_creature_id)")
            self.engine.execute(sql, {'id': event.id, 'guild_id': event.guild.id, 'timestamp': event.timestamp, 'free_creature_id': event.free_creature.id})

    def get_events(self, timestamp_start: int, timestamp_end: int) -> list[Event]:
        results = []
        tables = ['RegionRechargeEvents', 'CreatureRechargeEvents', 'FreeCreatureProtectedEvents', 'FreeCreatureExpiresEvents']
        for table in tables:
            sql = text(f"SELECT * FROM {table} WHERE timestamp BETWEEN :start AND :end")
            result = self.engine.execute(sql, {'start': timestamp_start, 'end': timestamp_end}).fetchall()
            results.extend(result)
        return results

    def add_guild(self, guild_id: int) -> Database.Guild:

        guild = PostgresDatabase.Guild(self, guild_id, self.start_condition.start_config)

        with self.parent.transaction():
            sql_guild = text("""
                INSERT INTO Guilds (guild_id, region_recharge, creature_recharge, free_protection, free_expire)
                VALUES (:guild_id, 10, 10, 5, 60)
            """)
            self.engine.execute(sql_guild, {'guild_id': guild_id})

            for base_region in self.start_condition.start_active_regions:
                guild.add_region(base_region)

            for base_creature in self.start_condition.start_available_creatures:
                guild.add_to_creature_pool(base_creature)


        return PostgresDatabase.Guild(self, guild_id, self.start_condition.start_config)

    def get_guilds(self):
        sql = text("SELECT guild_id, region_recharge, creature_recharge, free_protection, free_expire FROM Guilds")
        result = self.engine.execute(sql)
        guilds = [PostgresDatabase.Guild(self, row['guild_id'], {
            "region_recharge": row['region_recharge'],
            "creature_recharge": row['creature_recharge'],
            "free_protection": row['free_protection'],
            "free_expire": row['free_expire']
        }) for row in result]
        return guilds

    def get_guild(self, guild_id: int) -> Database.Guild:
        sql = text("SELECT guild_id, region_recharge, creature_recharge, free_protection, free_expire FROM Guilds WHERE guild_id = :guild_id")
        result = self.engine.execute(sql, {'guild_id': guild_id}).fetchone()

        if not result:
            raise GuildNotFound("None or too many guilds with this guild_id, needs to be unique")

        guild = PostgresDatabase.Guild(self, result['guild_id'], {
            "region_recharge": result['region_recharge'],
            "creature_recharge": result['creature_recharge'],
            "free_protection": result['free_protection'],
            "free_expire": result['free_expire']
        })

        return guild

    def remove_guild(self, guild: Database.Guild) -> Database.Guild:
        sql = text("DELETE FROM Guilds WHERE guild_id = :guild_id")
        self.engine.execute(sql, {'guild_id': guild.id})
        return guild

    class Guild(Database.Guild):

        def __init__(self, parent: Database, guild_id: int, config: dict):
            super().__init__(parent, guild_id)
            self.config = config

        def set_config(self, config: dict) -> None:
            sql = text("""
                UPDATE Guilds SET 
                    region_recharge = :region_recharge, 
                    creature_recharge = :creature_recharge, 
                    free_protection = :free_protection, 
                    free_expire = :free_expire 
                WHERE guild_id = :guild_id
            """)
            self.parent.engine.execute(sql, {
                'guild_id': self.id,
                'region_recharge': config['region_recharge'],
                'creature_recharge': config['creature_recharge'],
                'free_protection': config['free_protection'],
                'free_expire': config['free_expire']
            })
            self.config = config

        def get_config(self) -> dict:
            sql = text("SELECT region_recharge, creature_recharge, free_protection, free_expire FROM Guilds WHERE guild_id = :guild_id")
            result = self.parent.engine.execute(sql, {'guild_id': self.id}).fetchone()
            if result:
                self.config = {
                    'region_recharge': result['region_recharge'],
                    'creature_recharge': result['creature_recharge'],
                    'free_protection': result['free_protection'],
                    'free_expire': result['free_expire']
                }
            return self.config

        def fresh_region_id(self) -> int:
            sql = text("SELECT COALESCE(MAX(id), -1) + 1 AS next_id FROM Regions WHERE guild_id = :guild_id")
            result = self.parent.engine.execute(sql, {'guild_id': self.id}).scalar()
            return result

        def add_region(self, base_region: BaseRegion) -> Database.Region:
            region_id = self.fresh_region_id()
            sql = text("""
                INSERT INTO Regions (id, guild_id, base_region_id)
                VALUES (:id, :guild_id, :base_region_id)
            """)
            self.parent.engine.execute(sql, {'id': region_id, 'guild_id': self.id, 'base_region_id': base_region.id})
            return PostgresDatabase.Region(self.parent, region_id, base_region)

        def get_regions(self):
            sql = text("SELECT id, guild_id, base_region_id FROM Regions WHERE guild_id = :guild_id")
            results = self.parent.engine.execute(sql, {'guild_id': self.id}).fetchall()
            return [PostgresDatabase.Region(self.parent, row['id'], regions[row['base_region_id']], row['guild_id']) for row in results]

        def get_region(self, region_id: int) -> Database.Region:
            sql = text("SELECT id, guild_id, base_region_id FROM Regions WHERE id = :id AND guild_id = :guild_id")
            result = self.parent.engine.execute(sql, {'id': region_id, 'guild_id': self.id}).fetchone()
            if not result:
                raise RegionNotFound("None or too many regions with this base region, needs to be unique")
            return PostgresDatabase.Region(self.parent, result['id'], regions[result['base_region_id']], result['guild_id'])

        def remove_region(self, region: Database.Region) -> Database.Region:
            sql = text("DELETE FROM Regions WHERE id = :id AND guild_id = :guild_id")
            self.parent.engine.execute(sql, {'id': region.id, 'guild_id': self.id})
            return region

        def add_player(self, player_id: int) -> Database.Player:
            player = PostgresDatabase.Player(self.parent, self, player_id)

            with self.parent.transaction():
                sql_player = text("INSERT INTO Players (id, guild_id) VALUES (:player_id, :guild_id)")

                self.parent.engine.execute(sql_player, {'player_id': player_id, 'guild_id': self.id})

                for base_creature in self.parent.start_condition.start_deck:
                    creature = self.add_creature(base_creature, player)
                    player.add_to_discard(creature)

            return 

        def get_players(self):
            sql = text("SELECT id FROM Players WHERE guild_id = :guild_id")
            results = self.parent.engine.execute(sql, {'guild_id': self.id}).fetchall()
            return [PostgresDatabase.Player(self.parent, self, row['id']) for row in results]

        def get_player(self, player_id: int) -> Database.Player:
            sql = text("SELECT id FROM Players WHERE guild_id = :guild_id AND id = :player_id")
            result = self.parent.engine.execute(sql, {'guild_id': self.id, 'player_id': player_id}).fetchone()
            if not result:
                raise PlayerNotFound("None or too many players with this player_id, needs to be unique")
            return PostgresDatabase.Player(self.parent, self, result['id'])

        def remove_player(self, player: Database.Player) -> Database.Player:
            sql = text("DELETE FROM Players WHERE guild_id = :guild_id AND id = :player_id")
            self.parent.engine.execute(sql, {'guild_id': self.id, 'player_id': player.id})
            return player

        def fresh_creature_id(self) -> int:
            sql = text("SELECT COALESCE(MAX(id), -1) + 1 FROM Creatures WHERE guild_id = :guild_id")
            result = self.parent.engine.execute(sql, {'guild_id': self.id}).scalar()
            return result

        def add_creature(self, creature: BaseCreature, owner: Database.Player) -> Database.Creature:
            creature_id = self.fresh_creature_id()
            sql = text("""
                INSERT INTO Creatures (id, guild_id, base_creature_id, owner_id)
                VALUES (:id, :guild_id, :base_creature_id, :owner_id)
            """)
            self.parent.engine.execute(sql, {'id': creature_id, 'guild_id': self.id, 'base_creature_id': creature.id, 'owner_id': owner.id})
            return PostgresDatabase.Creature(self.parent, creature_id, creature, self, owner)

        def get_creatures(self):
            sql = text("SELECT id, base_creature_id, owner_id FROM Creatures WHERE guild_id = :guild_id")
            results = self.parent.engine.execute(sql, {'guild_id': self.id}).fetchall()
            return [PostgresDatabase.Creature(self.parent, row['id'], creatures[row['base_creature_id']], self, row['owner_id']) for row in results]

        def get_creature(self, creature_id: int) -> Database.Creature:
            sql = text("SELECT id, base_creature_id, owner_id FROM Creatures WHERE id = :creature_id AND guild_id = :guild_id")
            result = self.parent.engine.execute(sql, {'creature_id': creature_id, 'guild_id': self.id}).fetchone()
            if not result:
                raise CreatureNotFound("None or too many creatures with this id, needs to be unique")
            return PostgresDatabase.Creature(self.parent, result['id'], creatures[result['base_creature_id']], self, result['owner_id'])

        def remove_creature(self, creature: Database.Creature):
            sql = text("DELETE FROM Creatures WHERE id = :id AND guild_id = :guild_id")
            self.parent.engine.execute(sql, {'id': creature.id, 'guild_id': self.id})
            return creature

        def add_to_creature_pool(self, base_creature: BaseCreature):
            sql = text("INSERT INTO BaseCreatures (id, guild_id) VALUES (:id, :guild_id)")
            self.parent.engine.execute(sql, {'id': base_creature.id, 'guild_id': self.id})

        def get_creature_pool(self):
            sql = text("SELECT id FROM BaseCreatures WHERE guild_id = :guild_id")
            results = self.parent.engine.execute(sql, {'guild_id': self.id}).fetchall()
            return [result['id'] for result in results]

        def get_random_from_creature_pool(self) -> int:
            creature_pool = self.get_creature_pool()
            if not creature_pool:
                raise ValueError("Creature pool is empty")
            return random.choice(creature_pool)

        def remove_from_creature_pool(self, base_creature: BaseCreature):
            sql = text("DELETE FROM BaseCreatures WHERE id = :id AND guild_id = :guild_id")
            self.parent.engine.execute(sql, {'id': base_creature.id, 'guild_id': self.id})

        def add_free_creature(self, base_creature: BaseCreature, channel_id: int, message_id: int, roller_id: int) -> Database.FreeCreature:
            timestamp_protected = self.parent.timestamp_after(self.config["free_protection"])
            timestamp_expires = self.parent.timestamp_after(self.config["free_expire"])
            sql = text("""
                INSERT INTO FreeCreatures (base_creature_id, guild_id, channel_id, message_id, roller_id, timestamp_protected, timestamp_expires)
                VALUES (:base_creature_id, :guild_id, :channel_id, :message_id, :roller_id, :timestamp_protected, :timestamp_expires)
            """)
            self.parent.engine.execute(sql, {
                'base_creature_id': base_creature.id,
                'guild_id': self.id,
                'channel_id': channel_id,
                'message_id': message_id,
                'roller_id': roller_id,
                'timestamp_protected': timestamp_protected,
                'timestamp_expires': timestamp_expires
            })
            return PostgresDatabase.FreeCreature(self.parent, base_creature, self, channel_id, message_id, roller_id, timestamp_protected, timestamp_expires)

        def get_free_creatures(self):
            sql = text("SELECT * FROM FreeCreatures WHERE guild_id = :guild_id")
            results = self.parent.engine.execute(sql, {'guild_id': self.id}).fetchall()
            return [PostgresDatabase.FreeCreature(self.parent, creatures[row['base_creature_id']], self, row['channel_id'], row['message_id'], row['roller_id'], row['timestamp_protected'], row['timestamp_expires']) for row in results]

        def get_free_creature(self, channel_id: int, message_id: int) -> Database.FreeCreature:
            sql = text("SELECT * FROM FreeCreatures WHERE guild_id = :guild_id AND channel_id = :channel_id AND message_id = :message_id")
            result = self.parent.engine.execute(sql, {'guild_id': self.id, 'channel_id': channel_id, 'message_id': message_id}).fetchone()
            if not result:
                raise CreatureNotFound("None or too many creatures with this id, needs to be unique")
            return PostgresDatabase.FreeCreature(self.parent, creatures[result['base_creature_id']], self, result['channel_id'], result['message_id'], result['roller_id'], result['timestamp_protected'], result['timestamp_expires'])

        def remove_free_creature(self, creature: Database.FreeCreature):
            sql = text("DELETE FROM FreeCreatures WHERE guild_id = :guild_id AND channel_id = :channel_id AND message_id = :message_id")
            self.parent.engine.execute(sql, {'guild_id': self.id, 'channel_id': creature.channel_id, 'message_id': creature.message_id})
            return creature

    class Region(Database.Region):

        def __init__(self, parent: Database, id: int, region: BaseRegion, guild: Database.Guild):
            super().__init__(parent, id, region, guild)

        def occupy(self, creature: Database.Creature):
            with self.parent.transaction():
                if self.is_occupied():
                    raise Exception("Trying to occupy an occupied region")

                until = self.parent.timestamp_after(self.guild.get_config()["region_recharge"])
                sql = text("""
                    INSERT INTO Occupies (guild_id, creature_id, region_id, timestamp_occupied)
                    VALUES (:guild_id, :creature_id, :region_id, :timestamp)
                """)
                self.parent.engine.execute(sql, {
                    'guild_id': self.guild.id,
                    'creature_id': creature.id,
                    'region_id': self.id,
                    'timestamp': until
                })

                event_id = self.parent.fresh_event_id(self.guild)
                self.parent.add_event(Event(event_id, self.parent, until, self.guild))

        def unoccupy(self, current: int):
            with self.parent.transaction():
                occupant, until = self.occupied()
                if occupant is None:
                    raise Exception("Trying to unoccupy an already free region")
                if current < until:
                    raise Exception("Trying to unoccupy with too early timestamp")

                sql = text("DELETE FROM Occupies WHERE guild_id = :guild_id AND region_id = :region_id")
                self.parent.engine.execute(sql, {'guild_id': self.guild.id, 'region_id': self.id})
                self.occupant = None

        def occupied(self) -> tuple[Database.Creature, int]:
            sql = text("SELECT creature_id, timestamp_occupied FROM Occupies WHERE guild_id = :guild_id AND region_id = :region_id")
            result = self.parent.engine.execute(sql, {'guild_id': self.guild.id, 'region_id': self.id}).fetchone()
            if result:
                creature = Database.Creature(self.parent, result['creature_id'], self.guild)
                return (creature, result['timestamp_occupied'])
            return (None, None)

        def is_occupied(self) -> bool:
            sql = text("SELECT COUNT(*) FROM Occupies WHERE guild_id = :guild_id AND region_id = :region_id")
            count = self.parent.engine.execute(sql, {'guild_id': self.guild.id, 'region_id': self.id}).scalar()
            return count > 0

    class Player(Database.Player):
        def __init__(self, parent: Database, guild_id: int, user_id: int):
            super().__init__(parent, guild_id, user_id)

        def get_resources(self):
            sql = text("SELECT resource_type, quantity FROM Resources WHERE player_id = :player_id AND guild_id = :guild_id")
            results = self.parent.engine.execute(sql, {'player_id': self.user_id, 'guild_id': self.guild_id}).fetchall()
            return {Resource(result['resource_type']): result['quantity'] for result in results}

        def set_resources(self, resources: dict[Resource, int]):
            with self.parent.transaction():
                for resource_type, quantity in resources.items():
                    sql = text("""
                        UPDATE Resources SET quantity = :quantity 
                        WHERE player_id = :player_id AND guild_id = :guild_id AND resource_type = :resource_type
                    """)
                    self.parent.engine.execute(sql, {'quantity': quantity, 'player_id': self.user_id, 'guild_id': self.guild_id, 'resource_type': int(resource_type)})

        def has(self, resource: Resource, amount: int) -> bool:
            sql = text("SELECT quantity FROM Resources WHERE player_id = :player_id AND guild_id = :guild_id AND resource_type = :resource_type")
            result = self.parent.engine.execute(sql, {'player_id': self.user_id, 'guild_id': self.guild_id, 'resource_type': int(resource)}).scalar()
            return result >= amount if result else False

        def give(self, resource: Resource, amount: int):
            sql = text("""
                UPDATE Resources SET quantity = quantity + :amount 
                WHERE player_id = :player_id AND guild_id = :guild_id AND resource_type = :resource_type
            """)
            self.parent.engine.execute(sql, {'amount': amount, 'player_id': self.user_id, 'guild_id': self.guild_id, 'resource_type': int(resource)})

        def get_deck(self):
            sql = text("SELECT creature_id FROM Deck WHERE player_id = :player_id AND guild_id = :guild_id")
            results = self.parent.engine.execute(sql, {'player_id': self.user_id, 'guild_id': self.guild_id}).fetchall()
            return [result['creature_id'] for result in results]

        def get_hand(self):
            sql = text("SELECT creature_id FROM Hand WHERE player_id = :player_id AND guild_id = :guild_id ORDER BY order")
            results = self.parent.engine.execute(sql, {'player_id': self.user_id, 'guild_id': self.guild_id}).fetchall()
            return [result['creature_id'] for result in results]

        def get_discard(self):
            sql = text("SELECT creature_id FROM Discard WHERE player_id = :player_id AND guild_id = :guild_id")
            results = self.parent.engine.execute(sql, {'player_id': self.user_id, 'guild_id': self.guild_id}).fetchall()
            return [result['creature_id'] for result in results]

        def draw_card_raw(self):
            
            with self.parent.transaction():
                sql = text("""
                    SELECT creature_id FROM Deck 
                    WHERE player_id = :player_id AND guild_id = :guild_id 
                    ORDER BY RANDOM() 
                    LIMIT 1
                """)
                result = self.parent.engine.execute(sql, {'player_id': self.user_id, 'guild_id': self.guild_id}).fetchone()

                if not result:
                    raise EmptyDeckException()

                drawn_card = result['creature_id']

                sql = text("""
                    DELETE FROM Deck 
                    WHERE player_id = :player_id AND guild_id = :guild_id AND creature_id = :creature_id
                """)
                self.parent.engine.execute(sql, {'player_id': self.user_id, 'guild_id': self.guild_id, 'creature_id': drawn_card})

                sql = text("""
                    INSERT INTO Hand (player_id, guild_id, creature_id, order)
                    VALUES (:player_id, :guild_id, :creature_id, (SELECT COALESCE(MAX(order), 0) + 1 FROM Hand WHERE player_id = :player_id AND guild_id = :guild_id))
                """)
                self.parent.engine.execute(sql, {'player_id': self.user_id, 'guild_id': self.guild_id, 'creature_id': drawn_card})

            return drawn_card

        def reshuffle_discard(self):
            with self.parent.transaction():
                discard = self.get_discard()
                for creature_id in discard:
                    sql = text("DELETE FROM Discard WHERE player_id = :player_id AND guild_id = :guild_id AND creature_id = :creature_id")
                    self.parent.engine.execute(sql, {'player_id': self.user_id, 'guild_id': self.guild_id, 'creature_id': creature_id})
                    sql = text("INSERT INTO Deck (player_id, guild_id, creature_id) VALUES (:player_id, :guild_id, :creature_id)")
                    self.parent.engine.execute(sql, {'player_id': self.user_id, 'guild_id': self.guild_id, 'creature_id': creature_id})

        def delete_creature_from_hand(self, creature: Database.Creature):
            sql = text("DELETE FROM Hand WHERE player_id = :player_id AND guild_id = :guild_id AND creature_id = :creature_id")
            self.parent.engine.execute(sql, {'player_id': self.user_id, 'guild_id': self.guild_id, 'creature_id': creature.id})

        def play_creature(self, creature: Database.Creature):
            sql = text("DELETE FROM Hand WHERE player_id = :player_id AND guild_id = :guild_id AND creature_id = :creature_id")
            self.parent.engine.execute(sql, {'player_id': self.user_id, 'guild_id': self.guild_id, 'creature_id': creature.id})
            sql = text("INSERT INTO Played (player_id, guild_id, creature_id) VALUES (:player_id, :guild_id, :creature_id)")
            self.parent.engine.execute(sql, {'player_id': self.user_id, 'guild_id': self.guild_id, 'creature_id': creature.id})

        def add_to_discard(self, creature: Database.Creature):
            sql = text("INSERT INTO Discard (player_id, guild_id, creature_id) VALUES (:player_id, :guild_id, :creature_id)")
            self.parent.engine.execute(sql, {'player_id': self.user_id, 'guild_id': self.guild_id, 'creature_id': creature.id})

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

        def get_protected_timestamp(self) -> int:
            sql = text("""
                SELECT timestamp_protected FROM FreeCreatures
                WHERE guild_id = :guild_id AND channel_id = :channel_id AND message_id = :message_id
            """)
            result = self.parent.engine.execute(sql, {
                'guild_id': self.guild.id, 'channel_id': self.channel_id, 'message_id': self.message_id
            }).scalar()
            return result

        def get_expires_timestamp(self) -> int:
            sql = text("""
                SELECT timestamp_expires FROM FreeCreatures
                WHERE guild_id = :guild_id AND channel_id = :channel_id AND message_id = :message_id
            """)
            result = self.parent.engine.execute(sql, {
                'guild_id': self.guild.id, 'channel_id': self.channel_id, 'message_id': self.message_id
            }).scalar()
            return result

        def claimed(self):
            sql = text("""
                DELETE FROM FreeCreatures
                WHERE guild_id = :guild_id AND channel_id = :channel_id AND message_id = :message_id
            """)
            self.parent.engine.execute(sql, {
                'guild_id': self.guild.id, 'channel_id': self.channel_id, 'message_id': self.message_id
            })
            self.remove_related_events()

        def remove_related_events(self):
            with self.parent.transaction():

                sql_protected = text("""
                    DELETE FROM FreeCreatureProtectedEvents
                    WHERE guild_id = :guild_id AND free_creature_id = :free_creature_id
                """)
                self.parent.engine.execute(sql_protected, {
                    'guild_id': self.guild.id,
                    'free_creature_id': self.id
                })

                sql_expires = text("""
                    DELETE FROM FreeCreatureExpiresEvents
                    WHERE guild_id = :guild_id AND free_creature_id = :free_creature_id
                """)
                self.parent.engine.execute(sql_expires, {
                    'guild_id': self.guild.id,
                    'free_creature_id': self.id
                })
