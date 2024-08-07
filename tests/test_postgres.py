import time
from typing import (
    cast,
    List,
    Tuple,
    Union,
    Optional,
    Type,
    TypeVar,
    Callable,
    Awaitable,
    Coroutine,
    Any,
)

import sqlalchemy
from testcontainers.postgres import PostgresContainer  # type: ignore

from src.core.base_types import (
    BaseResources,
    Resource,
    Event,
    Gain,
    Price,
)
from src.core.exceptions import (
    GuildNotFound,
    PlayerNotFound,
    NotEnoughResourcesException,
    EmptyDeckException,
)
from src.definitions.start_condition import start_condition
from src.database.database import Database
from src.database.postgres import PostgresDatabase
from src.definitions.creatures import *
from src.definitions.regions import *

K = TypeVar("K")


def is_subset(a: List[K], b: List[K]) -> bool:
    for e in a:
        if e not in b:
            return False
    return True


def are_subsets(a: List[K], b: List[K]) -> bool:
    for e in a:
        if e not in b:
            return False
    for e in b:
        if e not in a:
            return False
    return True


def subtract(a: List[K], b: List[K]) -> List[K]:
    new = []
    for e in a:
        if e not in b:
            new.append(e)
    return new


T = TypeVar("T", bound=Event)


def events_by_type(
    guild_db: Database.Guild, t: Type[T], start: Optional[float] = None, end: Optional[float] = None
) -> List[T]:
    if start is None:
        start = time.time() - 60
    if end is None:
        end = time.time() + 10

    return cast(List[T], guild_db.get_events(start, end, event_type=t))


postgres = PostgresContainer("postgres:16").start()

engine = sqlalchemy.create_engine(postgres.get_connection_url())
test_db = PostgresDatabase(start_condition, engine)


def test_guild_creation() -> None:
    guild_db: Database.Guild = test_db.add_guild(1)

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


def test_player_creation() -> None:
    guild_db: Database.Guild = test_db.add_guild(1)

    try:
        assert are_subsets(
            [
                guild_db.get_region(e.region_id).region
                for e in events_by_type(guild_db, Database.Guild.RegionAddedEvent)
            ],
            start_condition.start_active_regions,
        )

        player1_db: Database.Player = guild_db.add_player(1)
        assert guild_db.get_player(player1_db.id) == player1_db
        assert guild_db.get_players() == [player1_db]
        assert are_subsets(
            [
                guild_db.get_player(e.player_id)
                for e in events_by_type(guild_db, Database.Guild.PlayerAddedEvent)
            ],
            [player1_db],
        )

        player2_db: Database.Player = guild_db.add_player(2)
        assert are_subsets(guild_db.get_players(), [player1_db, player2_db])
        assert are_subsets(
            [
                guild_db.get_player(e.player_id)
                for e in events_by_type(guild_db, Database.Guild.PlayerAddedEvent)
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
            [e.player_id for e in events_by_type(guild_db, Database.Guild.PlayerRemovedEvent)],
            [player1_db.id],
        )

        assert guild_db.get_players() == [player2_db]

    finally:
        test_db.remove_guild(guild_db)
        assert test_db.get_guilds() == []


def test_player_resources() -> None:
    guild_db: Database.Guild = test_db.add_guild(1)

    try:
        player1_db: Database.Player = guild_db.add_player(1)

        for res in BaseResources:
            assert player1_db.has(res, 0) == True
            assert player1_db.has(res, 1) == False

        get_events: Callable[[], List[Event]] = lambda: events_by_type(
            guild_db, Database.Player.PlayerGainEvent
        ) + events_by_type(guild_db, Database.Player.PlayerPayEvent)
        assert len(get_events()) == 0

        for i in [1, 2, 5, 100]:
            for res in BaseResources:
                prev_events = get_events()

                player1_db.give(res, i)

                new_events = subtract(get_events(), prev_events)
                assert len(new_events) == 1
                new_event = cast(Database.Player.PlayerGainEvent, new_events[0])
                assert new_event.event_type == Database.Player.PlayerGainEvent.event_type
                assert new_event.player_id == player1_db.id
                assert new_event.changes == [(res.value, i)]

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
                new_event2 = cast(Database.Player.PlayerPayEvent, new_events[0])
                assert new_event2.event_type == Database.Player.PlayerPayEvent.event_type
                assert new_event2.player_id == player1_db.id
                assert new_event2.changes == [(res.value, i)]

    finally:
        test_db.remove_guild(guild_db)
        assert test_db.get_guilds() == []


def test_player_prices() -> None:
    guild_db: Database.Guild = test_db.add_guild(1)

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


def test_deck() -> None:
    guild_db: Database.Guild = test_db.add_guild(1)

    try:
        player5_db: Database.Player = guild_db.add_player(5)

        assert are_subsets(
            [c.creature for c in player5_db.get_deck()],
            start_condition.start_deck,
        )

        get_events: Callable[[], List[Database.Player.PlayerDrawEvent]] = lambda: events_by_type(
            guild_db, Database.Player.PlayerDrawEvent
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

            player6_db: Database.Player = guild_db.add_player(6)

            assert [c.creature for c in player6_db.get_deck()] == start_condition.start_deck
            assert player6_db.get_hand() == []

            cards_drawn, reshuffled, hand_full = player6_db.draw_cards(N=i)

            all_events = get_events()
            assert len(all_events) == i + 1
            new_events = subtract(all_events, prev_events)
            assert len(new_events) == 1
            assert new_events[0].event_type == Database.Player.PlayerDrawEvent.event_type
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
        player7_db: Database.Player = guild_db.add_player(7)
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

        assert is_subset(
            [c.creature for c in player7_db.get_hand()],
            start_condition.start_deck,
        )

    finally:
        test_db.remove_guild(guild_db)
        assert test_db.get_guilds() == []


def test_playing() -> None:
    guild_db: Database.Guild = test_db.add_guild(1)

    try:
        player8_db: Database.Player = guild_db.add_player(8)
        assert [c.creature for c in player8_db.get_deck()] == start_condition.start_deck

        player8_db.draw_cards(5)
        assert are_subsets(
            [c.creature for c in player8_db.get_full_deck()],
            start_condition.start_deck,
        )
        for c in player8_db.get_hand():
            assert c.creature in start_condition.start_deck

        creature2_db: Database.Creature = player8_db.get_hand()[0]
        assert isinstance(creature2_db.creature, Commoner)

        region1_db: Database.Region = guild_db.get_regions()[0]
        assert region1_db.occupied() == (None, None)
        assert isinstance(region1_db.region, Village)

        resources: dict[Resource, int] = player8_db.get_resources()

        # needs an order to actually be able to play it
        player8_db.gain([Gain(Resource.ORDERS, 1)])

        assert player8_db.get_played() == []

        prev_gain_events = events_by_type(guild_db, Database.Player.PlayerGainEvent)
        assert len(prev_gain_events) == 1
        assert len(events_by_type(guild_db, Database.Player.PlayerPayEvent)) == 0
        assert len(events_by_type(guild_db, Database.Player.PlayerPlayToRegionEvent)) == 0
        assert len(events_by_type(guild_db, Database.Creature.CreatureRechargeEvent)) == 0

        player8_db.play_creature_to_region(creature2_db, region1_db)

        new_gain_event: Database.Player.PlayerGainEvent = subtract(
            events_by_type(guild_db, Database.Player.PlayerGainEvent),
            prev_gain_events,
        )[0]
        assert new_gain_event.event_type == Database.Player.PlayerGainEvent.event_type
        assert new_gain_event.changes == [(Resource.INTEL.value, 1)]

        new_pay_event: Database.Player.PlayerPayEvent = events_by_type(
            guild_db, Database.Player.PlayerPayEvent
        )[0]
        assert new_pay_event.event_type == Database.Player.PlayerPayEvent.event_type
        assert new_pay_event.changes == [(Resource.ORDERS.value, 1)]

        new_play_event: Database.Player.PlayerPlayToRegionEvent = events_by_type(
            guild_db, Database.Player.PlayerPlayToRegionEvent
        )[0]
        assert new_play_event.event_type == Database.Player.PlayerPlayToRegionEvent.event_type
        assert guild_db.get_player(new_play_event.player_id) == player8_db
        assert guild_db.get_creature(new_play_event.creature_id) == creature2_db
        assert guild_db.get_region(new_play_event.region_id) == region1_db
        assert new_play_event.play_extra_data == {}

        new_creature_recharge_event: Database.Creature.CreatureRechargeEvent = events_by_type(
            guild_db,
            Database.Creature.CreatureRechargeEvent,
            end=time.time() + 10 + guild_db.get_config()["creature_recharge"],
        )[0]
        assert guild_db.get_creature(new_creature_recharge_event.creature_id) == creature2_db
        assert new_creature_recharge_event.timestamp > new_play_event.timestamp

        new_region_recharge_event: Database.Region.RegionRechargeEvent = events_by_type(
            guild_db,
            Database.Region.RegionRechargeEvent,
            end=time.time() + 10 + guild_db.get_config()["region_recharge"],
        )[0]
        assert guild_db.get_region(new_region_recharge_event.region_id) == region1_db
        assert new_region_recharge_event.timestamp > new_play_event.timestamp

        assert player8_db.get_played()[0][0] == creature2_db

        resources[Resource.INTEL] += 1
        assert player8_db.get_resources() == resources

        assert region1_db.occupied()[0] == creature2_db
        assert len(player8_db.get_hand()) == 4

        # campaign

        creature3_db: Database.Creature = player8_db.get_hand()[0]
        assert isinstance(creature3_db.creature, Commoner)

        resources2: dict[Resource, int] = player8_db.get_resources()

        assert player8_db.get_campaign() == []
        old_deck = player8_db.get_full_deck()

        assert events_by_type(guild_db, Database.Player.PlayerPlayToCampaignEvent) == []

        player8_db.play_creature_to_campaign(creature3_db)

        campaign_event: Database.Player.PlayerPlayToCampaignEvent = events_by_type(
            guild_db, Database.Player.PlayerPlayToCampaignEvent
        )[0]
        assert guild_db.get_creature(campaign_event.creature_id) == creature3_db
        assert guild_db.get_player(campaign_event.player_id) == player8_db

        assert player8_db.get_campaign() == [(creature3_db, 0)]
        assert are_subsets(subtract(old_deck, [creature3_db]), player8_db.get_full_deck())

        resources2[Resource.RALLY] += 1
        assert player8_db.get_resources() == resources2

    finally:
        test_db.remove_guild(guild_db)
        assert test_db.get_guilds() == []


def test_claim() -> None:
    guild_db = test_db.add_guild(1)

    try:
        player8_db = guild_db.add_player(8)

        player8_db.gain([Gain(Resource.RALLY, 1)])

        assert player8_db.get_resources()[Resource.RALLY] == 1
        resources: dict[Resource, int] = player8_db.get_resources()

        free_creature1_db = guild_db.add_free_creature(Commoner(), 0, 0, player8_db)

        assert (
            events_by_type(
                guild_db,
                Database.FreeCreature.FreeCreatureProtectedEvent,
                end=time.time() * 2,
            )
            == []
        )
        assert (
            events_by_type(
                guild_db,
                Database.FreeCreature.FreeCreatureExpiresEvent,
                end=time.time() * 2,
            )
            == []
        )

        free_creature1_db.create_events()

        protected_event: Database.FreeCreature.FreeCreatureProtectedEvent = events_by_type(
            guild_db,
            Database.FreeCreature.FreeCreatureProtectedEvent,
            end=time.time() * 2,
        )[0]
        assert (
            guild_db.get_free_creature(protected_event.channel_id, protected_event.message_id)
            == free_creature1_db
        )
        assert protected_event.timestamp == free_creature1_db.get_protected_timestamp()

        expires_event: Database.FreeCreature.FreeCreatureExpiresEvent = events_by_type(
            guild_db,
            Database.FreeCreature.FreeCreatureExpiresEvent,
            end=time.time() * 2,
        )[0]
        assert (
            guild_db.get_free_creature(expires_event.channel_id, protected_event.message_id)
            == free_creature1_db
        )
        assert expires_event.timestamp == free_creature1_db.get_expires_timestamp()

        assert free_creature1_db.is_protected(time.time())
        assert not free_creature1_db.is_expired(time.time())

        assert events_by_type(guild_db, Database.FreeCreature.FreeCreatureClaimedEvent) == []

        free_creature1_db.claim(time.time() + guild_db.get_config()["free_protection"], player8_db)

        claimed_event = events_by_type(guild_db, Database.FreeCreature.FreeCreatureClaimedEvent)[0]

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


def test_recharge() -> None:
    guild_db: Database.Guild = test_db.add_guild(1)

    try:
        config = guild_db.get_config()
        player8_db: Database.Player = guild_db.add_player(8)

        recharges = player8_db.get_recharges()
        assert recharges["player_order_recharge"].event_type == "player_order_recharge"
        assert recharges["player_order_recharge"].timestamp > time.time()
        assert (
            recharges["player_order_recharge"].timestamp
            < time.time() + config["order_recharge"] + 1
        )

        assert recharges["player_magic_recharge"].event_type == "player_magic_recharge"
        assert recharges["player_magic_recharge"].timestamp > time.time()
        assert (
            recharges["player_magic_recharge"].timestamp
            < time.time() + config["magic_recharge"] + 1
        )

        assert recharges["player_card_recharge"].event_type == "player_card_recharge"
        assert recharges["player_card_recharge"].timestamp > time.time()
        assert (
            recharges["player_card_recharge"].timestamp < time.time() + config["card_recharge"] + 1
        )

        # now we refresh the events
        # order
        order_recharge_event: Database.Player.PlayerOrderRechargeEvent = cast(
            Database.Player.PlayerOrderRechargeEvent, recharges["player_order_recharge"]
        )

        resources = player8_db.get_resources()
        order_recharge_event.resolve()
        resources[Resource.ORDERS] += 1
        assert player8_db.get_resources() == resources

        guild_db.remove_event(order_recharge_event)

        # magic
        magic_recharge_event: Database.Player.PlayerMagicRechargeEvent = cast(
            Database.Player.PlayerMagicRechargeEvent, recharges["player_magic_recharge"]
        )

        resources = player8_db.get_resources()
        magic_recharge_event.resolve()
        resources[Resource.MAGIC] += 1
        assert player8_db.get_resources() == resources

        guild_db.remove_event(magic_recharge_event)

        # cards
        card_recharge_event: Database.Player.PlayerCardRechargeEvent = cast(
            Database.Player.PlayerCardRechargeEvent, recharges["player_card_recharge"]
        )
        hand = player8_db.get_hand()
        card_recharge_event.resolve()
        assert is_subset(hand, player8_db.get_hand())
        assert len(hand) + 1 == len(player8_db.get_hand())

        guild_db.remove_event(card_recharge_event)

        # events refreshed, check invariants
        recharges = player8_db.get_recharges()
        assert recharges["player_order_recharge"].event_type == "player_order_recharge"
        assert recharges["player_order_recharge"].timestamp > time.time()
        assert (
            recharges["player_order_recharge"].timestamp
            < time.time() + config["order_recharge"] + 1
        )

        assert recharges["player_magic_recharge"].event_type == "player_magic_recharge"
        assert recharges["player_magic_recharge"].timestamp > time.time()
        assert (
            recharges["player_magic_recharge"].timestamp
            < time.time() + config["magic_recharge"] + 1
        )

        assert recharges["player_card_recharge"].event_type == "player_card_recharge"
        assert recharges["player_card_recharge"].timestamp > time.time()
        assert (
            recharges["player_card_recharge"].timestamp < time.time() + config["card_recharge"] + 1
        )

    finally:
        test_db.remove_guild(guild_db)
        assert test_db.get_guilds() == []


def test_rollback() -> None:
    guild_db1: Database.Guild = test_db.add_guild(1)
    guild_db2: Database.Guild = test_db.add_guild(2)

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


import asyncio
from src.event_resolver.resolver import (
    add_notification_function,
    listen_to_notifications,
    KeepAlive,
)


def event_handler_factory(
    db: PostgresDatabase, events: List[Event]
) -> Callable[[Any, Any, Any, str], None]:

    def event_handler(connection: Any, pid: Any, channel: Any, payload: str) -> None:
        with db.transaction() as con:
            event = db.get_event_by_id(int(payload), con=con)
            events.append(event)

    return event_handler


def add_player_async_factory(guild_db: Database.Guild) -> Coroutine[Any, Any, Any]:

    async def add_player_async() -> Any:
        await asyncio.sleep(2)
        return guild_db.add_player(1)

    return add_player_async()


async def event_loop_test(
    guild_db: Database.Guild, test_function: Callable[[Database.Guild], Awaitable[Any]]
) -> Tuple[Any, List[Event]]:
    keep_alive = KeepAlive()

    events: List[Event] = []

    listener_task = asyncio.create_task(
        listen_to_notifications(
            test_db, event_handler_factory(test_db, events), keep_alive=keep_alive
        )
    )

    r = await test_function(guild_db)

    await asyncio.sleep(2)
    keep_alive.stop()

    await listener_task

    return r, events


def are_event_type_subsets(a: List[Event], b: List[Event], event_type: Type[Event]) -> bool:
    return are_subsets(
        [e for e in a if isinstance(e, event_type)], [e for e in b if isinstance(e, event_type)]
    )


def test_event_resolver() -> None:
    add_notification_function(test_db)
    guild_db: Database.Guild = test_db.add_guild(1)

    try:
        time.sleep(2)
        event_loop_time = time.time()

        r, events = asyncio.run(event_loop_test(guild_db, add_player_async_factory))
        guild_events = guild_db.get_events(0, time.time() * 2)

        assert are_subsets(events, guild_db.get_events(event_loop_time, time.time() * 2))

        assert is_subset(events, guild_db.get_events(0, time.time() * 2))
        assert not are_event_type_subsets(events, guild_events, Database.Guild.RegionAddedEvent)
        assert are_event_type_subsets(events, guild_events, Database.Guild.PlayerAddedEvent)
        assert are_event_type_subsets(events, guild_events, Database.Player.PlayerCardRechargeEvent)
        assert are_event_type_subsets(
            events, guild_events, Database.Player.PlayerMagicRechargeEvent
        )
        assert are_event_type_subsets(
            events, guild_events, Database.Player.PlayerOrderRechargeEvent
        )

    finally:
        test_db.remove_guild(guild_db)
        assert test_db.get_guilds() == []
