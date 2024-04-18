from src.core.base_types import Resource, Region, StartCondition, Database
from src.core.base_types import GuildNotFound, PlayerNotFound, NotEnoughResourcesException
from src.core.regions import start_condition
from src.core.database import TestDatabase


def test_basic():
    test_db = TestDatabase(start_condition)
    guild_db = test_db.add_guild(1)

    assert test_db.get_guild(guild_db.guild_id) == guild_db
    assert guild_db.regions == start_condition.start_active_regions

    player1_db = guild_db.add_player(1)

    assert guild_db.get_player(player1_db.user_id) == player1_db
    assert player1_db.has(Resource.GOLD, 0) == True
    assert player1_db.has(Resource.GOLD, 1) == False

    player1_db.give(Resource.GOLD, 1)
    assert player1_db.has(Resource.GOLD, 0) == True
    assert player1_db.has(Resource.GOLD, 1) == True

    player1_db.remove(Resource.GOLD, 1)
    assert player1_db.has(Resource.GOLD, 0) == True
    assert player1_db.has(Resource.GOLD, 1) == False

    guild_db.remove_player(player1_db.user_id)
    got_error = False
    try:
        guild_db.get_player(player1_db)
    except PlayerNotFound:
        got_error = True

    assert got_error

    test_db.remove_guild(guild_db.guild_id)
    got_error = False
    try:
        test_db.get_guild(guild_db.guild_id)
    except GuildNotFound:
        got_error = True

    assert got_error
