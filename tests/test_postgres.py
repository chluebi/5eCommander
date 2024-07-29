import time

import sqlalchemy
from testcontainers.postgres import PostgresContainer

from src.core.base_types import BaseResources, Resource, BaseRegion, StartCondition, Event
from src.core.exceptions import (
    GuildNotFound,
    PlayerNotFound,
    NotEnoughResourcesException,
    EmptyDeckException,
)
from src.core.start_condition import start_condition
from src.database.database import Database
from src.database.postgres import PostgresDatabase
from src.core.creatures import *
from src.core.regions import *


def is_subset(a: list, b: list):
    for e in a:
        if e not in b:
            return False
    return True


def are_subsets(a: list, b: list):
    for e in a:
        if e not in b:
            return False
    for e in b:
        if e not in a:
            return False
    return True


def subtract(a: list, b: list):
    new = []
    for e in a:
        if e not in b:
            new.append(e)
    return new


def events_by_type(guild_db: PostgresDatabase.Guild, t: str) -> Event:
    return [e for e in guild_db.get_events(time.time() - 60, time.time() + 10) if e.event_type == t]


postgres = PostgresContainer("postgres:16").start()

engine = sqlalchemy.create_engine(postgres.get_connection_url())
test_db = PostgresDatabase(start_condition, engine)


def test_guild_creation():
    guild_db: PostgresDatabase.Guild = test_db.add_guild(1)

    try:
        assert test_db.get_guild(guild_db.id) == guild_db
        assert test_db.get_guilds() == [guild_db]
        assert [r.region for r in guild_db.get_regions()] == start_condition.start_active_regions
        assert [
            c for c in guild_db.get_creature_pool()
        ] == start_condition.start_available_creatures
    finally:
        test_db.remove_guild(guild_db)

        try:
            test_db.get_guild(guild_db.id)
            assert False
        except GuildNotFound:
            pass

        assert test_db.get_guilds() == []


def test_player_creation():
    guild_db: PostgresDatabase.Guild = test_db.add_guild(1)

    try:
        assert are_subsets(
            [
                guild_db.get_region(e.region_id).region
                for e in events_by_type(
                    guild_db, PostgresDatabase.Guild.RegionAddedEvent.event_type
                )
            ],
            start_condition.start_active_regions,
        )

        player1_db: Database.Player = guild_db.add_player(1)
        assert guild_db.get_player(player1_db.id) == player1_db
        assert guild_db.get_players() == [player1_db]
        assert are_subsets(
            [
                guild_db.get_player(e.player_id)
                for e in events_by_type(
                    guild_db, PostgresDatabase.Guild.PlayerAddedEvent.event_type
                )
            ],
            [player1_db],
        )

        player2_db: Database.Player = guild_db.add_player(2)
        assert are_subsets(guild_db.get_players(), [player1_db, player2_db])
        assert are_subsets(
            [
                guild_db.get_player(e.player_id)
                for e in events_by_type(
                    guild_db, PostgresDatabase.Guild.PlayerAddedEvent.event_type
                )
            ],
            [player1_db, player2_db],
        )

        guild_db.remove_player(player1_db)
        try:
            guild_db.get_player(player1_db.id)
            assert False
        except PlayerNotFound:
            pass
        assert are_subsets(
            [
                e.player_id
                for e in events_by_type(
                    guild_db, PostgresDatabase.Guild.PlayerRemovedEvent.event_type
                )
            ],
            [player1_db.id],
        )

        assert guild_db.get_players() == [player2_db]

    finally:
        test_db.remove_guild(guild_db)
        assert test_db.get_guilds() == []


def test_player_resources():
    guild_db: PostgresDatabase.Guild = test_db.add_guild(1)

    try:
        player1_db: PostgresDatabase.Player = guild_db.add_player(1)

        for res in BaseResources:
            assert player1_db.has(res, 0) == True
            assert player1_db.has(res, 1) == False

        get_events = lambda: events_by_type(
            guild_db, PostgresDatabase.Player.PlayerGainEvent.event_type
        ) + events_by_type(guild_db, PostgresDatabase.Player.PlayerPayEvent.event_type)
        assert len(get_events()) == 0

        for i in [1, 2, 5, 100]:
            for res in BaseResources:
                prev_events = get_events()

                player1_db.give(res, i)

                new_events = subtract(get_events(), prev_events)
                assert len(new_events) == 1
                assert (
                    new_events[0].event_type == PostgresDatabase.Player.PlayerGainEvent.event_type
                )
                assert new_events[0].player_id == player1_db.id
                assert new_events[0].changes == [(res.value, i)]

                for res2 in BaseResources:
                    if res2 == res:
                        assert player1_db.has(res2, i) == True
                        assert player1_db.has(res2, i + 1) == False
                    else:
                        assert player1_db.has(res2, i) == False

                prev_events = get_events()

                player1_db.remove(res, i)

                new_events = subtract(get_events(), prev_events)
                assert len(new_events) == 1
                assert new_events[0].event_type == PostgresDatabase.Player.PlayerPayEvent.event_type
                assert new_events[0].player_id == player1_db.id
                assert new_events[0].changes == [(res.value, i)]

    finally:
        test_db.remove_guild(guild_db)
        assert test_db.get_guilds() == []


def test_player_prices():
    guild_db: PostgresDatabase.Guild = test_db.add_guild(1)

    try:
        player1_db: Database.Player = guild_db.add_player(1)

        r = player1_db.get_resources()
        for res in BaseResources:
            assert r[res] == 0

        for res in BaseResources:
            assert player1_db.has(res, 0) == True
            assert player1_db.has(res, 1) == False

        gains = [
            [Gain(Resource.GOLD, 1)],
            [Gain(Resource.GOLD, 2), Gain(Resource.ORDERS, 1)],
            [Gain(Resource.STRENGTH, 100), Gain(Resource.ORDERS, 5)],
        ]

        prices = [
            [Price(Resource.GOLD, 1)],
            [Price(Resource.GOLD, 2), Price(Resource.ORDERS, 1)],
            [Price(Resource.STRENGTH, 100), Price(Resource.ORDERS, 5)],
        ]

        r = player1_db.get_resources()
        for res in BaseResources:
            assert r[res] == 0

        player1_db.gain(gains[0])
        assert player1_db.fulfills_price(prices[0])
        assert not player1_db.fulfills_price(prices[1])
        assert not player1_db.fulfills_price(prices[2])
        player1_db.pay_price(prices[0])

        r = player1_db.get_resources()
        for res in BaseResources:
            assert r[res] == 0

        player1_db.gain(gains[1])
        assert player1_db.fulfills_price(prices[0])
        assert player1_db.fulfills_price(prices[1])
        assert not player1_db.fulfills_price(prices[2])
        player1_db.pay_price(prices[1])

        r = player1_db.get_resources()
        for res in BaseResources:
            assert r[res] == 0

        player1_db.gain(gains[2])
        assert not player1_db.fulfills_price(prices[0])
        assert not player1_db.fulfills_price(prices[1])
        assert player1_db.fulfills_price(prices[2])
        player1_db.pay_price(prices[2])

        r = player1_db.get_resources()
        for res in BaseResources:
            assert r[res] == 0

    finally:
        test_db.remove_guild(guild_db)
        assert test_db.get_guilds() == []


def test_deck():
    guild_db: PostgresDatabase.Guild = test_db.add_guild(1)

    try:
        player5_db: PostgresDatabase.Player = guild_db.add_player(5)

        assert [c.creature for c in player5_db.get_deck()] == start_condition.start_deck

        for _ in start_condition.start_deck:
            assert player5_db.draw_card_raw().creature in start_condition.start_deck

        for _ in range(10):
            got_error = False
            try:
                player5_db.draw_card_raw()
                assert False
            except EmptyDeckException:
                pass

        for i in range(len(start_condition.start_deck) * 2):
            player6_db: PostgresDatabase.Player = guild_db.add_player(6)

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
        player7_db: PostgresDatabase.Player = guild_db.add_player(7)
        assert [c.creature for c in player7_db.get_deck()] == start_condition.start_deck

        creature1_db: PostgresDatabase.Creature = guild_db.add_creature(Commoner(), player7_db)
        player7_db.add_to_discard(creature1_db)

        assert player7_db.get_discard() == [creature1_db]

        # draw entire deck
        cards_drawn, reshuffled = player7_db.draw_cards(N=len(start_condition.start_deck))

        assert len(cards_drawn) == len(start_condition.start_deck)
        assert len(player7_db.get_deck()) == 0

        player7_db.draw_cards(N=1)
        assert len(player7_db.get_hand()) == len(start_condition.start_deck) + 1

    finally:
        test_db.remove_guild(guild_db)
        assert test_db.get_guilds() == []


def test_playing():
    guild_db: PostgresDatabase.Guild = test_db.add_guild(1)

    try:
        player8_db: PostgresDatabase.Player = guild_db.add_player(8)
        assert [c.creature for c in player8_db.get_deck()] == start_condition.start_deck

        player8_db.draw_cards(5)
        assert are_subsets(
            [c.creature for c in player8_db.get_full_deck()], start_condition.start_deck
        )
        for c in player8_db.get_hand():
            assert c.creature in start_condition.start_deck

        creature2_db: PostgresDatabase.Creature = player8_db.get_hand()[0]
        assert isinstance(creature2_db.creature, Commoner)

        region1_db: PostgresDatabase.Region = guild_db.get_regions()[0]
        assert region1_db.occupied() == (None, None)
        assert isinstance(region1_db.region, Village)

        resources: dict[Resource, int] = player8_db.get_resources()

        # needs an order to actually be able to play it
        player8_db.gain([Gain(Resource.ORDERS, 1)])
        player8_db.play_creature_to_region(creature2_db, region1_db)

        resources[Resource.WORKERS] += 1
        assert player8_db.get_resources() == resources

        assert region1_db.occupied()[0] == creature2_db
        assert len(player8_db.get_hand()) == 4

        # campaign

        creature3_db: PostgresDatabase.Creature = player8_db.get_hand()[0]
        assert isinstance(creature3_db.creature, Commoner)

        resources: dict[Resource, int] = player8_db.get_resources()

        player8_db.play_creature_to_campaign(creature3_db)

        resources[Resource.RALLY] += 1
        assert player8_db.get_resources() == resources

    finally:
        test_db.remove_guild(guild_db)
        assert test_db.get_guilds() == []


def test_claim():
    guild_db: PostgresDatabase.Guild = test_db.add_guild(1)

    try:
        player8_db: PostgresDatabase.Player = guild_db.add_player(8)

        player8_db.gain([Gain(Resource.RALLY, 1)])

        assert player8_db.get_resources()[Resource.RALLY] == 1
        resources: dict[Resource, int] = player8_db.get_resources()

        free_creature1_db: PostgresDatabase.FreeCreature = guild_db.add_free_creature(
            Commoner(), 0, 0, player8_db
        )

        assert free_creature1_db.is_protected(time.time())
        assert not free_creature1_db.is_expired(time.time())

        free_creature1_db.claim(time.time() + guild_db.get_config()["free_protection"], player8_db)

        resources[Resource.RALLY] -= 1
        assert player8_db.get_resources() == resources

    finally:
        test_db.remove_guild(guild_db)
        assert test_db.get_guilds() == []


def test_rollback():
    guild_db1: PostgresDatabase.Guild = test_db.add_guild(1)
    guild_db2: PostgresDatabase.Guild = test_db.add_guild(2)

    test_db.remove_guild(guild_db2)

    # now only guild 1 is in there

    try:
        with test_db.transaction(parent=None) as con:
            test_db.remove_guild(guild_db1, con=con)  # works
            test_db.get_guild(guild_db2.id, con=con)  # fails, whole transaction rolled back
    except GuildNotFound:
        pass

    # guild 1 should now still exist

    assert test_db.get_guild(guild_db1.id)

    test_db.remove_guild(guild_db1)
    assert test_db.get_guilds() == []
