import random
from copy import deepcopy

from src.core.base_types import (
    Resource,
    BaseResources,
    BaseRegion,
    BaseCreature,
    StartCondition,
    Database,
)
from src.core.base_types import (
    GuildNotFound,
    PlayerNotFound,
    CreatureNotFound,
    NotEnoughResourcesException,
    EmptyDeckException,
)


class TestDatabase(Database):

    def __init__(self, start_condition):
        super().__init__(start_condition)
        self.guilds: list[TestDatabase.Guild] = []

    def add_guild(self, guild_id: int) -> Database.Guild:
        guild = TestDatabase.Guild(self, guild_id, self.start_condition)
        self.guilds.append(guild)
        return guild

    def get_guild(self, guild_id: int) -> Database.Guild:
        guilds = [g for g in self.guilds if g.guild_id == guild_id]

        if len(guilds) != 1:
            raise GuildNotFound("None or too many guilds with this guild_id, needs to be unique")

        return guilds[0]

    def remove_guild(self, guild_id: int) -> Database.Guild:
        guild = self.get_guild(guild_id)
        self.guilds.remove(guild)
        return guild

    class Guild(Database.Guild):

        def __init__(self, parent: Database, guild_id: int, start_condition: StartCondition):
            super().__init__(parent, guild_id)
            self.players: list[TestDatabase.Player] = []
            self.regions: list[TestDatabase.Region] = deepcopy(start_condition.start_active_regions)
            self.creatures: list[TestDatabase.Creature] = []

        def add_player(self, user_id: int) -> Database.Player:
            player = TestDatabase.Player(self.parent, self.guild_id, user_id)
            self.players.append(player)
            return player

        def get_player(self, user_id: int) -> Database.Player:
            players = [p for p in self.players if p.user_id == user_id]

            if len(players) != 1:
                raise PlayerNotFound(
                    "None or too many players with this user_id, needs to be unique"
                )

            return players[0]

        def remove_player(self, user_id: int) -> Database.Player:
            player = self.get_player(user_id)
            self.players.remove(player)
            return player

        def add_creature(self, creature: BaseCreature, owner_id: int) -> Database.Creature:
            if len(self.creatures) == 0:
                id = 0
            else:
                id = max(c.id for c in self.creatures)
            creature = TestDatabase.Creature(self.parent, creature, self.guild_id, owner_id, id)
            self.creatures.append(creature)
            return creature

        def get_creature(self, creature_id: int):
            creatures = [c for c in creatures if c.id == creature_id]

            if len(creatures) != 1:
                raise CreatureNotFound(
                    "None or too many players with this user_id, needs to be unique"
                )

            return creatures[0]

        def remove_creature(self, creature_id: int):
            creature = self.get_creature(creature_id)
            self.players.remove(creature)
            return creature

    class Region(Database.Region):

        def __init__(self, parent: Database, region: BaseRegion):
            super().__init__(parent, region)

    class Player(Database.Player):

        def __init__(self, parent: Database, guild_id: int, user_id: int):
            super().__init__(parent, guild_id, user_id)
            self.resources: dict[Resource, int] = {r: 0 for r in BaseResources}
            guild: TestDatabase.Guild = self.parent.get_guild(self.guild_id)
            self.deck: list[Database.Creature] = [guild.add_creature(c, self.user_id) for c in self.parent.start_condition.start_deck]
            self.hand: list[Database.Creature] = []
            self.discard: list[Database.Creature] = []

        def get_resources(self):
            return deepcopy(self.resources)

        def set_resources(self, resources: dict[Resource, int]):
            self.resources = deepcopy(resources)

        def get_deck(self):
            return self.deck

        def get_hand(self):
            return self.hand

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

        def delete_creature_from_hand(self, creature_id: int) -> None:
            creatures = [c for c in self.get_hand() if c.id == creature_id]

            if len(creatures) != 1:
                raise CreatureNotFound(
                    "None or too many players with this user_id, needs to be unique"
                )
            creature = creatures[0]

            self.hand.remove(creature)
            parent: TestDatabase = self.parent
            parent.get_guild(self.guild_id).remove_creature(creature_id)

        def add_to_discard(self, creature: Database.Creature) -> None:
            self.discard.append(creature)

    class Creature(Database.Creature):

        def __init__(self, parent, creature: BaseCreature, guild_id: int, owner_id: int, id: int):

            super().__init__(parent, creature, guild_id, owner_id, id)
