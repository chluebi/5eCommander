from enum import Enum
from collections import namedtuple


class GuildNotFound(Exception):
    pass


class PlayerNotFound(Exception):
    pass


class NotEnoughResourcesException(Exception):
    pass


Resource = Enum(
    "Resource",
    ["ORDER", "GOLD", "ARTEFACTS", "WORKERS", "MAGIC", "RALLY", "STRENGTH"],
)

RegionCategory = namedtuple("RegionCategory", ["name", "emoji"])


class Region:

    name = "default_region"
    category = None

    def __init__(self):
        pass

    def mission(self, player):
        return


class StartCondition:

    def __init__(self, start_active_regions: list[Region]):
        self.start_active_regions = start_active_regions


class Database:

    def __init__(self, start_condition: StartCondition):
        self.start_condition = start_condition

    def transaction_start(self):
        pass

    def transaction_end(self):
        pass

    def add_guild(self, guild_id: int):
        pass

    def get_guild(self, guild_id: int):
        pass

    def remove_guild(self, guild_id: int):
        pass

    class Region:

        def __init__(self, region: Region):
            self.region = region

    class Guild:

        def __init__(self, guild_id: int):
            self.guild_id = guild_id

        def add_player(self, user_id: int):
            pass

        def get_player(self, user_id: int):
            pass

        def remove_player(self, player):
            pass

    class Player:

        def __init__(self, guild_id: int, user_id: int):
            self.guild_id = guild_id
            self.user_id = user_id

        def has(self, resource: Resource, amount: int) -> bool:
            pass

        def give(self, resource: Resource, amount: int) -> None:
            pass

        def remove(self, resource: Resource, amount: int) -> None:
            self.give(resource, -amount)
