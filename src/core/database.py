import random
from copy import deepcopy

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


class TestDatabase(Database):

    def __init__(self, start_condition):
        super().__init__(start_condition)
        self.guilds: list[TestDatabase.Guild] = []
        self.events: list[Event] = []

    def fresh_event_id(self, guild):
        guild_events = [e for e in self.events if e.guild == guild]
        if len(guild_events) == 0:
            return 0
        max_id = max([e.id for e in self.events])
        return max_id + 1

    def add_event(self, event: Event):
        self.events.append(event)

    def get_events(self, timestamp_start: int, timestamp_end: int):
        return [
            e
            for e in self.events
            if timestamp_start <= e.timestamp and timestamp_end >= e.timestamp
        ]

    def add_guild(self, guild_id: int) -> Database.Guild:
        guild = TestDatabase.Guild(self, guild_id, self.start_condition)
        self.guilds.append(guild)
        return guild

    def get_guilds(self):
        return self.guilds

    def get_guild(self, guild_id: int) -> Database.Guild:
        guilds = [g for g in self.guilds if g.id == guild_id]

        if len(guilds) != 1:
            raise GuildNotFound("None or too many guilds with this guild_id, needs to be unique")

        return guilds[0]

    def remove_guild(self, guild: Database.Guild) -> Database.Guild:
        self.guilds.remove(guild)
        return guild

    class Guild(Database.Guild):

        def __init__(
            self,
            parent: Database,
            guild_id: int,
            start_condition: StartCondition,
        ):
            super().__init__(parent, guild_id, start_condition)
            self.config = start_condition.start_config
            self.players: list[TestDatabase.Player] = []
            self.regions: list[TestDatabase.Region] = []

            for r in start_condition.start_active_regions:
                self.add_region(r)

            self.creatures: list[TestDatabase.Creature] = []

        def set_config(self, config: dict) -> None:
            self.config = config

        def get_config(self) -> dict:
            return self.config

        def fresh_region_id(self) -> int:
            if len(self.regions) == 0:
                return 0
            max_id = max([r.id for r in self.regions])
            return max_id + 1

        def add_region(self, region: BaseRegion) -> Database.Region:
            region = TestDatabase.Region(self.fresh_region_id(), self.parent, region, self)
            self.regions.append(region)
            return region

        def get_regions(self):
            return self.regions

        def get_region(self, region: BaseRegion) -> Database.Region:
            regions = [r for r in self.regions if r.region == region]

            if len(regions) != 1:
                raise RegionNotFound(
                    "None or too many regions with this base region, needs to be unique"
                )

            return regions[0]

        def remove_region(self, region: BaseRegion) -> Database.Region:
            region = self.get_region(region)
            self.regions.remove(region)
            return region

        def add_player(self, user_id: int) -> Database.Player:
            player = TestDatabase.Player(self.parent, self, user_id)
            self.players.append(player)
            return player

        def get_players(self):
            return self.players

        def get_player(self, user_id: int) -> Database.Player:
            players = [p for p in self.players if p.id == user_id]

            if len(players) != 1:
                raise PlayerNotFound(
                    "None or too many players with this user_id, needs to be unique"
                )

            return players[0]

        def remove_player(self, player: Database.Player) -> Database.Player:
            self.players.remove(player)
            return player

        def add_creature(self, creature: BaseCreature, owner: Database.Player) -> Database.Creature:
            if len(self.creatures) == 0:
                id = 0
            else:
                id = max(c.id for c in self.creatures) + 1
            creature = TestDatabase.Creature(self.parent, creature, self, owner, id)
            self.creatures.append(creature)
            return creature

        def get_creatures(self):
            return self.creatures

        def get_creature(self, creature_id: int):
            creatures = [c for c in self.creatures if c.id == creature_id]

            if len(creatures) != 1:
                raise CreatureNotFound(
                    "None or too many creatures with this id, needs to be unique"
                )

            return creatures[0]

        def remove_creature(self, creature: Database.Creature):
            self.players.remove(creature)
            return creature

    class Region(Database.Region):

        def __init__(self, id: int, parent: Database, region: BaseRegion, guild: Database.Guild):
            super().__init__(id, parent, region, guild)
            self.occupant = None

        def occupy(self, creature: Database.Creature):
            if self.occupant is not None:
                Exception("Trying to occupy an occupied region")

            until = self.parent.timestamp_after(self.guild.get_config()["region_recharge"])
            self.occupant = (creature, until)
            self.parent.add_event(
                Database.Region.RegionRechargeEvent(
                    self.parent.fresh_event_id(self.guild), self.parent, self.guild, until, self
                )
            )

        def unoccupy(self, current: int):
            if self.occupant is None:
                Exception("Trying to unoccupy an already free region")

            if current < self.occupant[1]:
                Exception("Trying to unoccupy with too early timestamp")

            creature: Database.Creature = self.occupant[0]
            creature.owner.add_to_discard(creature)
            self.occupant = None

        def occupied(self) -> tuple[Database.Creature, int]:
            return self.occupant

    class Player(Database.Player):

        def __init__(self, parent: Database, guild_id: int, user_id: int):
            super().__init__(parent, guild_id, user_id)
            self.resources: dict[Resource, int] = {r: 0 for r in BaseResources}
            self.deck: list[Database.Creature] = [
                self.guild.add_creature(c, self) for c in self.parent.start_condition.start_deck
            ]
            self.hand: list[Database.Creature] = []
            self.played: list[Database.Creature] = []
            self.discard: list[Database.Creature] = []

        def get_resources(self):
            return deepcopy(self.resources)

        def set_resources(self, resources: dict[Resource, int]):
            self.resources = deepcopy(resources)

        def get_deck(self):
            return self.deck

        def get_hand(self):
            return self.hand

        def get_played(self):
            return self.played

        def get_discard(self):
            return self.discard

        def has(self, resource: Resource, amount: int) -> bool:
            return self.resources[resource] >= amount

        def give(self, resource: Resource, amount: int):
            self.resources[resource] += amount

        def draw_card_raw(self) -> None:
            if len(self.deck) == 0:
                raise EmptyDeckException()

            drawn_card = random.choice(self.deck)
            self.deck.remove(drawn_card)
            self.hand.append(drawn_card)
            return drawn_card

        def reshuffle_discard(self) -> None:
            self.deck += self.discard
            self.discard = []

        def delete_creature_from_hand(self, creature: Database.Creature) -> None:
            self.hand.remove(creature)
            parent: TestDatabase = self.parent
            parent.get_guild(self.guild_id).remove_creature(creature)

        def play_creature(self, creature: Database.Creature) -> None:
            self.hand.remove(creature)
            self.played.append(creature)

        def add_to_discard(self, creature: Database.Creature) -> None:
            self.discard.append(creature)

    class Creature(Database.Creature):

        def __init__(
            self,
            parent,
            creature: BaseCreature,
            guild: Database.Guild,
            owner: Database.Player,
            id: int,
        ):

            super().__init__(parent, creature, guild, owner, id)
