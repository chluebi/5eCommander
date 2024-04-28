import time
from src.core.base_types import Resource, BaseRegion, StartCondition, Database
from src.core.base_types import (
    GuildNotFound,
    PlayerNotFound,
    NotEnoughResourcesException,
    EmptyDeckException,
)
from src.core.start_condition import start_condition
from src.core.database import TestDatabase
from src.core.creatures import *
from src.core.regions import *


def are_subsets(a: list, b: list):
    for e in a:
        if e not in b:
            return False
    for e in b:
        if e not in a:
            return False
    return True


def test_text():
    commoner = Commoner()

    assert commoner.quest_ability_effect_text() == ""
    assert commoner.campaign_ability_effect_text() == "gain 1 🚩rally"

    village = Village()

    assert village.quest_effect_text() == "gain 1 ⚒️worker"

    small_mine = SmallMine()

    assert small_mine.quest_effect_text() == "pay 5 🪙gold -> gain 1 ⚒️worker"


def test_basic_db():
    test_db = TestDatabase(start_condition)
    guild_db = test_db.add_guild(1)

    assert test_db.get_guild(guild_db.id) == guild_db
    assert [r.region for r in guild_db.get_regions()] == start_condition.start_active_regions

    player1_db = guild_db.add_player(1)

    assert guild_db.get_player(player1_db.id) == player1_db
    assert player1_db.has(Resource.GOLD, 0) == True
    assert player1_db.has(Resource.GOLD, 1) == False

    player1_db.give(Resource.GOLD, 1)
    assert player1_db.has(Resource.GOLD, 0) == True
    assert player1_db.has(Resource.GOLD, 1) == True

    player1_db.remove(Resource.GOLD, 1)
    assert player1_db.has(Resource.GOLD, 0) == True
    assert player1_db.has(Resource.GOLD, 1) == False

    guild_db.remove_player(player1_db)
    got_error = False
    try:
        guild_db.get_player(player1_db)
    except PlayerNotFound:
        got_error = True

    assert got_error

    test_db.remove_guild(guild_db)
    got_error = False
    try:
        test_db.get_guild(guild_db.id)
    except GuildNotFound:
        got_error = True

    assert got_error

    guild_db = test_db.add_guild(1)

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
        assert not player4_db.fulfills_price([Gain(Resource.GOLD, 1) for j in range(i + 1)])
        assert not player4_db.fulfills_price([Gain(Resource.GOLD, i + 1)])

        player4_db.pay_price([Gain(Resource.GOLD, 1) for j in range(i)])

    # deck and drawing
    player5_db: TestDatabase.Player = guild_db.add_player(5)

    assert [c.creature for c in player5_db.get_deck()] == start_condition.start_deck

    for _ in start_condition.start_deck:
        assert player5_db.draw_card_raw().creature in start_condition.start_deck

    for _ in range(10):
        got_error = False
        try:
            player5_db.draw_card_raw()
        except EmptyDeckException:
            got_error = True
        assert got_error

    for i in range(len(start_condition.start_deck) * 2):
        player6_db: TestDatabase.Player = guild_db.add_player(6)

        assert [c.creature for c in player6_db.get_deck()] == start_condition.start_deck

        cards_drawn, reshuffled = player6_db.draw_cards(N=i)

        assert len(cards_drawn) == min(i, len(start_condition.start_deck))
        if i <= len(start_condition.start_deck):
            assert not reshuffled
        else:
            assert reshuffled

        for card in cards_drawn:
            assert card.creature in start_condition.start_deck

        guild_db.remove_player(player6_db)

    # drawing creatures
    player7_db: TestDatabase.Player = guild_db.add_player(7)
    assert [c.creature for c in player7_db.get_deck()] == start_condition.start_deck

    creature1_db: TestDatabase.Creature = guild_db.add_creature(Commoner(), player7_db.id)
    player7_db.add_to_discard(creature1_db)

    assert player7_db.get_discard() == [creature1_db]

    # draw entire deck
    cards_drawn, reshuffled = player7_db.draw_cards(N=len(start_condition.start_deck))

    assert len(cards_drawn) == len(start_condition.start_deck)
    assert len(player7_db.get_deck()) == 0

    player7_db.draw_cards(N=1)
    assert len(player7_db.get_hand()) == len(start_condition.start_deck) + 1

    # playing creatures
    player8_db: TestDatabase.Player = guild_db.add_player(8)
    assert [c.creature for c in player8_db.get_deck()] == start_condition.start_deck

    player8_db.draw_cards(5)
    assert are_subsets([c.creature for c in player8_db.get_full_deck()], start_condition.start_deck)
    for c in player8_db.get_hand():
        assert c.creature in start_condition.start_deck

    creature2_db: TestDatabase.Creature = player8_db.get_hand()[0]
    assert isinstance(creature2_db.creature, Commoner)

    region1_db: TestDatabase.Region = guild_db.get_regions()[0]
    assert region1_db.occupied() is None
    assert isinstance(region1_db.region, Village)

    assert len(test_db.get_events(0, time.time() * 2)) == 0

    resources: dict[Resource, int] = player8_db.get_resources()

    # needs an order to actually be able to play it
    player8_db.gain([Gain(Resource.ORDERS, 1)])
    player8_db.play_creature_to_region(creature2_db, region1_db)

    resources[Resource.WORKERS] += 1
    assert player8_db.get_resources() == resources

    assert len(test_db.get_events(0, time.time() * 2)) == 2
    assert test_db.get_events(0, time.time() * 2)[0].timestamp > time.time()

    assert region1_db.occupied()[0] == creature2_db
    assert len(player8_db.get_hand()) == 4

    # campaign

    creature3_db: TestDatabase.Creature = player8_db.get_hand()[0]
    assert isinstance(creature3_db.creature, Commoner)

    resources: dict[Resource, int] = player8_db.get_resources()

    player8_db.play_creature_to_campaign(creature3_db)

    resources[Resource.RALLY] += 1
    assert player8_db.get_resources() == resources

    # claim creatures

    assert player8_db.get_resources()[Resource.RALLY] >= 1
    resources: dict[Resource, int] = player8_db.get_resources()

    free_creature1_db: TestDatabase.FreeCreature = guild_db.add_free_creature(
        Commoner(), 0, 0, player8_db
    )

    assert free_creature1_db.is_protected(time.time())
    assert not free_creature1_db.is_expired(time.time())

    free_creature1_db.claim(time.time(), player8_db)

    resources[Resource.RALLY] -= 1
    assert player8_db.get_resources() == resources
