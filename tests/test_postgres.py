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


def events_by_type(guild_db: PostgresDatabase.Guild, t: str, start=None, end=None) -> Event:
    if start is None:
        start = time.time() - 60
    if end is None:
        end = time.time() + 10

    return [e for e in guild_db.get_events(start, end) if e.event_type == t]


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

        assert are_subsets([c.creature for c in player5_db.get_deck()], start_condition.start_deck)

        get_events = lambda: events_by_type(
            guild_db, PostgresDatabase.Player.PlayerDrawEvent.event_type
        )

        for _ in start_condition.start_deck:
            assert player5_db.draw_card_raw().creature in start_condition.start_deck

        for _ in range(10):
            try:
                player5_db.draw_card_raw()
                assert False
            except EmptyDeckException:
                pass

        for i in range(len(start_condition.start_deck) * 2):

            prev_events = get_events()
            assert len(prev_events) == i

            player6_db: PostgresDatabase.Player = guild_db.add_player(6)

            assert [c.creature for c in player6_db.get_deck()] == start_condition.start_deck
            assert player6_db.get_hand() == []

            cards_drawn, reshuffled, hand_full = player6_db.draw_cards(N=i)

            all_events = get_events()
            assert len(all_events) == i + 1
            new_events = subtract(all_events, prev_events)
            assert len(new_events) == 1
            assert new_events[0].event_type == PostgresDatabase.Player.PlayerDrawEvent.event_type
            assert guild_db.get_player(new_events[0].player_id) == player6_db
            assert new_events[0].num_cards == len(cards_drawn)

            if i <= guild_db.get_config()["max_cards"]:
                assert len(cards_drawn) == min(i, len(start_condition.start_deck))
                if i <= len(start_condition.start_deck):
                    assert not reshuffled
                else:
                    assert reshuffled

                for card in cards_drawn:
                    assert card.creature in start_condition.start_deck
            else:
                assert hand_full
                assert len(cards_drawn) == guild_db.get_config()["max_cards"]

            guild_db.remove_player(player6_db)

        # drawing creatures
        player7_db: PostgresDatabase.Player = guild_db.add_player(7)
        assert [c.creature for c in player7_db.get_deck()] == start_condition.start_deck

        # draw entire deck
        cards_drawn, reshuffled, hand_full = player7_db.draw_cards(
            N=len(start_condition.start_deck)
        )

        assert len(cards_drawn) == len(start_condition.start_deck)
        assert len(player7_db.get_deck()) == 0

        # hand full
        cards_drawn, reshuffled, hand_full = player7_db.draw_cards(N=1)
        assert cards_drawn == []
        assert hand_full

        # remove a creature to make space
        player7_db.delete_creature_from_hand(player7_db.get_hand()[0])
        assert len(player7_db.get_hand()) == len(start_condition.start_deck) - 1

        # deck empty
        cards_drawn, reshuffled, hand_full = player7_db.draw_cards(N=1)
        assert cards_drawn == []
        assert player7_db.get_deck() == []

        # discard a creature
        creature_to_discard = player7_db.get_hand()[0]
        player7_db.discard_creature_from_hand(creature_to_discard)
        assert len(player7_db.get_hand()) == len(start_condition.start_deck) - 2
        assert player7_db.get_deck() == []

        # now drawing works as the discarded creature is reshuffled
        cards_drawn, reshuffled, hand_full = player7_db.draw_cards(N=1)
        assert reshuffled
        assert cards_drawn == [creature_to_discard]
        assert player7_db.get_deck() == []

        assert is_subset([c.creature for c in player7_db.get_hand()], start_condition.start_deck)

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

        prev_gain_events = events_by_type(
            guild_db, PostgresDatabase.Player.PlayerGainEvent.event_type
        )
        assert len(prev_gain_events) == 1
        assert len(events_by_type(guild_db, PostgresDatabase.Player.PlayerPayEvent.event_type)) == 0
        assert (
            len(
                events_by_type(guild_db, PostgresDatabase.Player.PlayerPlayToRegionEvent.event_type)
            )
            == 0
        )
        assert (
            len(
                events_by_type(guild_db, PostgresDatabase.Creature.CreatureRechargeEvent.event_type)
            )
            == 0
        )

        player8_db.play_creature_to_region(creature2_db, region1_db)

        new_gain_event: PostgresDatabase.Player.PlayerGainEvent = subtract(
            events_by_type(guild_db, PostgresDatabase.Player.PlayerGainEvent.event_type),
            prev_gain_events,
        )[0]
        assert new_gain_event.event_type == PostgresDatabase.Player.PlayerGainEvent.event_type
        assert new_gain_event.changes == [(Resource.SUPPLIES.value, 1)]

        new_pay_event: PostgresDatabase.Player.PlayerPayEvent = events_by_type(
            guild_db, PostgresDatabase.Player.PlayerPayEvent.event_type
        )[0]
        assert new_pay_event.event_type == PostgresDatabase.Player.PlayerPayEvent.event_type
        assert new_pay_event.changes == [(Resource.ORDERS.value, 1)]

        new_play_event: PostgresDatabase.Player.PlayerPlayToRegionEvent = events_by_type(
            guild_db, PostgresDatabase.Player.PlayerPlayToRegionEvent.event_type
        )[0]
        assert (
            new_play_event.event_type == PostgresDatabase.Player.PlayerPlayToRegionEvent.event_type
        )
        assert guild_db.get_player(new_play_event.player_id) == player8_db
        assert guild_db.get_creature(new_play_event.creature_id) == creature2_db
        assert guild_db.get_region(new_play_event.region_id) == region1_db
        assert new_play_event.play_extra_data == {}

        new_creature_recharge_event: PostgresDatabase.Creature.CreatureRechargeEvent = (
            events_by_type(guild_db, PostgresDatabase.Creature.CreatureRechargeEvent.event_type)[0]
        )
        assert guild_db.get_creature(new_creature_recharge_event.creature_id) == creature2_db
        assert new_creature_recharge_event.timestamp > new_play_event.timestamp

        new_region_recharge_event: PostgresDatabase.Region.RegionRechargeEvent = events_by_type(
            guild_db, PostgresDatabase.Region.RegionRechargeEvent.event_type
        )[0]
        assert guild_db.get_region(new_region_recharge_event.region_id) == region1_db
        assert new_region_recharge_event.timestamp > new_play_event.timestamp

        resources[Resource.SUPPLIES] += 1
        assert player8_db.get_resources() == resources

        assert region1_db.occupied()[0] == creature2_db
        assert len(player8_db.get_hand()) == 4

        # campaign

        creature3_db: PostgresDatabase.Creature = player8_db.get_hand()[0]
        assert isinstance(creature3_db.creature, Commoner)

        resources: dict[Resource, int] = player8_db.get_resources()

        assert player8_db.get_campaign() == []
        old_deck = player8_db.get_full_deck()

        assert (
            events_by_type(guild_db, PostgresDatabase.Player.PlayerPlayToCampaignEvent.event_type)
            == []
        )

        player8_db.play_creature_to_campaign(creature3_db)

        campaign_event: PostgresDatabase.Player.PlayerPlayToCampaignEvent = events_by_type(
            guild_db, PostgresDatabase.Player.PlayerPlayToCampaignEvent.event_type
        )[0]
        assert guild_db.get_creature(campaign_event.creature_id) == creature3_db
        assert guild_db.get_player(campaign_event.player_id) == player8_db

        assert player8_db.get_campaign() == [(creature3_db, 0)]
        assert are_subsets(subtract(old_deck, [creature3_db]), player8_db.get_full_deck())

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

        assert (
            events_by_type(
                guild_db,
                PostgresDatabase.FreeCreature.FreeCreatureProtectedEvent.event_type,
                end=time.time() * 2,
            )
            == []
        )
        assert (
            events_by_type(
                guild_db,
                PostgresDatabase.FreeCreature.FreeCreatureExpiresEvent.event_type,
                end=time.time() * 2,
            )
            == []
        )

        free_creature1_db.create_events()

        protected_event: PostgresDatabase.FreeCreature.FreeCreatureProtectedEvent = events_by_type(
            guild_db,
            PostgresDatabase.FreeCreature.FreeCreatureProtectedEvent.event_type,
            end=time.time() * 2,
        )[0]
        assert (
            guild_db.get_free_creature(protected_event.channel_id, protected_event.message_id)
            == free_creature1_db
        )
        assert protected_event.timestamp == free_creature1_db.get_protected_timestamp()

        expires_event: PostgresDatabase.FreeCreature.FreeCreatureExpiresEvent = events_by_type(
            guild_db,
            PostgresDatabase.FreeCreature.FreeCreatureExpiresEvent.event_type,
            end=time.time() * 2,
        )[0]
        assert (
            guild_db.get_free_creature(expires_event.channel_id, protected_event.message_id)
            == free_creature1_db
        )
        assert expires_event.timestamp == free_creature1_db.get_expires_timestamp()

        assert free_creature1_db.is_protected(time.time())
        assert not free_creature1_db.is_expired(time.time())

        assert (
            events_by_type(
                guild_db, PostgresDatabase.FreeCreature.FreeCreatureClaimedEvent.event_type
            )
            == []
        )

        free_creature1_db.claim(time.time() + guild_db.get_config()["free_protection"], player8_db)

        claimed_event: PostgresDatabase.FreeCreature.FreeCreatureClaimedEvent = events_by_type(
            guild_db, PostgresDatabase.FreeCreature.FreeCreatureClaimedEvent.event_type
        )[0]
        assert (
            guild_db.get_free_creature(claimed_event.channel_id, claimed_event.message_id)
            == free_creature1_db
        )
        assert guild_db.get_player(claimed_event.player_id) == player8_db
        assert guild_db.get_creature(claimed_event.creature_id) in player8_db.get_full_deck()

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
