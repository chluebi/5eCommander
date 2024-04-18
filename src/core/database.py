from src.core.base_types import Resource, Region, StartCondition, Database
from src.core.base_types import GuildNotFound, PlayerNotFound, NotEnoughResourcesException


class TestDatabase(Database):

    def __init__(self, start_condition):
        super().__init__(start_condition)
        self.guilds: list[TestDatabase.Guild] = []

    def transaction_start(self):
        pass

    def transaction_end(self):
        pass

    def add_guild(self, guild_id: int) -> Database.Guild:
        guild = TestDatabase.Guild(guild_id, self.start_condition)
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

        def __init__(self, guild_id: int, start_condition: StartCondition):
            super().__init__(guild_id)
            self.players: list[TestDatabase.Player] = []
            self.regions: list[TestDatabase.Region] = start_condition.start_active_regions

        def add_player(self, user_id: int) -> Database.Player:
            player = TestDatabase.Player(self.guild_id, user_id)
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

    class Region(Database.Region):

        def __init__(self, region: Region):
            super().__init__(region)

    class Player(Database.Player):

        def __init__(self, guild_id, user_id):
            super().__init__(guild_id, user_id)
            self.resources: dict[Resource, int] = {r: 0 for r in list(Resource)}

        def has(self, resource: Resource, amount: int) -> bool:
            return self.resources[resource] >= amount

        def give(self, resource: Resource, amount: int):
            self.resources[resource] += amount

        def remove(self, resource: Resource, amount: int):
            self.give(resource, -amount)
