from src.core.base_types import Resource, Region, StartCondition, Database
from src.core.base_types import GuildNotFound, PlayerNotFound, NotEnoughResourcesException
from src.core.start_condition import start_condition
from src.core.database import TestDatabase
from src.core.creatures import *
from src.core.regions import *


def test_text():
    commoner = Commoner()

    assert commoner.quest_ability_effect_text() == ""
    assert commoner.rally_ability_effect_text() == "gain 1 🚩rally"

    village = Village()

    assert village.quest_effect_text() == "gain 1 ⚒️worker"

    small_mine = SmallMine()

    assert small_mine.quest_effect_text() == "pay 5 🪙gold -> gain 1 ⚒️worker"


def test_basic_db():
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


    # fulfills

    player2_db: TestDatabase.Player = guild_db.add_player(2)
    player2_db.give(Resource.GOLD, 1)

    price1 = [Price(Resource.GOLD, 1)]

    assert player2_db.fulfills_price(price1)

    player2_db.give(Resource.GOLD, 1)
    assert player2_db.fulfills_price(price1)

    player2_db.remove(Resource.GOLD, 2)
    assert not player2_db.fulfills_price(price1)


    price2 = [Price(Resource.GOLD, 1), Price(Resource.ARTEFACTS, 1)]
    assert not player2_db.fulfills_price(price2)

    player2_db.give(Resource.GOLD, 1)
    assert not player2_db.fulfills_price(price2)

    player2_db.remove(Resource.GOLD, 1)
    player2_db.give(Resource.ARTEFACTS, 1)
    assert not player2_db.fulfills_price(price2)

    player2_db.give(Resource.GOLD, 1)
    assert player2_db.fulfills_price(price2)


    price3 = [Price(Resource.GOLD, 1), Price(Resource.GOLD, 1)]

    assert not player2_db.fulfills_price(price3)

    player3_db: TestDatabase.Player = guild_db.add_player(3)
    assert not player3_db.fulfills_price(price3)

    player3_db.give(Resource.GOLD, 1)
    assert not player3_db.fulfills_price(price3)

    player3_db.give(Resource.GOLD, 1)
    assert player3_db.fulfills_price(price3)

    player3_db.remove(Resource.GOLD, 2)
    assert not player3_db.fulfills_price(price3)

    player3_db.give(Resource.GOLD, 2)
    assert player3_db.fulfills_price(price3)


    # pay, gain
    player4_db: TestDatabase.Player = guild_db.add_player(4)

    for i in range(1, 100):
        player4_db.gain([Gain(Resource.GOLD, 1) for j in range(i)])

        assert player4_db.fulfills_price([Gain(Resource.GOLD, 1) for j in range(i)])
        assert player4_db.fulfills_price([Gain(Resource.GOLD, i)])
        assert not player4_db.fulfills_price([Gain(Resource.GOLD, 1) for j in range(i+1)])
        assert not player4_db.fulfills_price([Gain(Resource.GOLD, i+1)])

        player4_db.pay_price([Gain(Resource.GOLD, 1) for j in range(i)])