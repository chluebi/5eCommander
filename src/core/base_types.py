from typing import Union
from enum import Enum
from collections import namedtuple, defaultdict

BASE_HANDS_SIZE = 5


class GuildNotFound(Exception):
    pass


class PlayerNotFound(Exception):
    pass


class NotEnoughResourcesException(Exception):
    pass


class EmptyDeckException(Exception):
    pass


Resource = Enum(
    "Resource",
    [
        "ORDERS",
        "GOLD",
        "ARTEFACTS",
        "WORKERS",
        "MAGIC",
        "RALLY",
        "STRENGTH",
        "CREATURES_IN_HAND",
        "KILL_CREATURES",
    ],
)

Price = namedtuple("Price", ["resource", "amount"], defaults=[Resource.GOLD, 0])
Gain = namedtuple("Gain", ["resource", "amount"], defaults=[Resource.GOLD, 0])
Choice = namedtuple("Choice", ["choices"], defaults=[[]])

Option = namedtuple("Option", ["price", "gain"], defaults=[[], []])


def resource_to_emoji(resource: Resource) -> str:
    match resource:
        case Resource.ORDERS:
            return "📜"
        case Resource.GOLD:
            return "🪙"
        case Resource.ARTEFACTS:
            return "🔮"
        case Resource.WORKERS:
            return "⚒️"
        case Resource.MAGIC:
            return "✨"
        case Resource.RALLY:
            return "🚩"
        case Resource.STRENGTH:
            return "🗡️"
        case Resource.CREATURES_IN_HAND:
            return "🃏"
        case Resource.KILL_CREATURES:
            return "👹"
        case _:
            return "❓"


def r_change_to_string(r_change: Union[Price | Gain]) -> str:

    change_text = ""
    if r_change.resource == Resource.CREATURES_IN_HAND:
        if isinstance(r_change, Price):
            change_text = "draw {0} {1}"
        else:
            raise Exception("Creatures in hand can only be drawn not lost")
    elif r_change.resource == Resource.KILL_CREATURES:
        change_text = "kill {0} {1} from your hand"
    elif r_change.resource == Resource.WORKERS and isinstance(r_change, Price):
        change_text = "use {0} {1}"
    elif isinstance(r_change, Gain):
        change_text = "gain {0} {1}"
    elif isinstance(r_change, Price):
        change_text = "pay {0} {1}"

    resource_text = ""
    if r_change.resource == Resource.CREATURES_IN_HAND:
        resource_text = "creatures"
    elif r_change.resource == Resource.KILL_CREATURES:
        resource_text = "creatures"
    else:
        resource_text = r_change.resource.name.lower()

    if r_change.amount == 1 and resource_text.endswith("s"):
        resource_text = resource_text[:-1]

    return change_text.format(r_change.amount, resource_to_emoji(r_change.resource) + resource_text)


def r_changes_to_string(r_changes: list[Price | Gain]) -> str:
    r_changes = [r_change for r_change in r_changes if r_change.amount != 0]

    prices = [r_change for r_change in r_changes if isinstance(r_change, Price)]
    gains = [r_change for r_change in r_changes if isinstance(r_change, Gain)]

    price_text = ", ".join([r_change_to_string(r_change) for r_change in prices])
    gains_text = ", ".join([r_change_to_string(r_change) for r_change in gains])

    if len(price_text) == 0 and len(gains_text) == 0:
        return ""
    if len(price_text) == 0:
        return f"{gains_text}"
    if len(gains_text) == 0:
        return f"{price_text}"

    return f"{price_text} -> {gains_text}"


RegionCategory = namedtuple("RegionCategory", ["name", "emoji"], defaults=["default_region", " "])


class Region:

    name = "default_region"
    category = None

    def __init__(self):
        pass

    def __repr__(self) -> str:
        return f"<Region: {self.name}>"

    def __eq__(self, other) -> bool:
        if isinstance(other, Region):
            return str(self) == str(other)
        return False

    def quest_effect_text(self) -> str:
        price, gains = self.quest_effect()
        return r_changes_to_string(price + gains)

    def quest_effect(self) -> tuple[list[Price], list[Gain]]:
        return [], []


class Creature:

    name = "default_creature"
    quest_regions: list[Region] = []

    def __init__(self):
        pass

    def __repr__(self) -> str:
        return f"<Creature: {self.name}>"

    def __eq__(self, other) -> bool:
        if isinstance(other, Creature):
            return str(self) == str(other)
        return False

    # questing
    def quest_ability_effect_text(self) -> str:
        price, gains = self.quest_ability_effect()
        return r_changes_to_string(price + gains)

    def quest_ability_effect(self) -> tuple[list[Price], list[Gain]]:
        return [], []

    # rallying
    def rally_ability_effect_text(self) -> str:
        price, gains = self.rally_ability_effect()
        return r_changes_to_string(price + gains)

    def rally_ability_effect(self) -> tuple[list[Price], list[Gain]]:
        return [], []


class StartCondition:

    def __init__(
        self,
        start_active_regions: list[Region],
        start_available_creatures: list[Creature],
        start_deck: list[Creature],
    ):
        self.start_active_regions = start_active_regions
        self.start_available_creatures = start_available_creatures
        self.start_deck = start_deck


class Database:

    def __init__(self, start_condition: StartCondition):
        self.start_condition = start_condition

    def start_transaction(self):
        pass

    def end_transaction(self):
        pass

    class Transaction:

        def __init__(self, parent, in_trans=False):
            self.parent = parent
            self.in_trans = in_trans

        def __enter__(self):
            if not self.in_trans:
                self.parent.start_transaction()
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            if not self.in_trans:
                self.parent.end_transaction()

    def add_guild(self, guild_id: int):
        pass

    def get_guild(self, guild_id: int):
        pass

    def remove_guild(self, guild_id: int):
        pass

    class Region:

        def __init__(self, parent, region: Region):
            self.parent = parent
            self.region = region

    class Guild:

        def __init__(self, parent, guild_id: int):
            self.parent = parent
            self.guild_id = guild_id

        def add_player(self, user_id: int):
            pass

        def get_player(self, user_id: int):
            pass

        def remove_player(self, player):
            pass

    class Player:

        def __init__(self, parent, guild_id: int, user_id: int):
            self.parent = parent
            self.guild_id = guild_id
            self.user_id = user_id

        def get_resources(self):
            pass

        def get_deck(self):
            pass

        def get_hand(self):
            pass

        def get_discard(self):
            pass

        def get_full_deck(self):
            return sorted(
                self.get_deck() + self.get_hand() + self.get_discard(), key=lambda x: str(x)
            )

        def has(self, resource: Resource, amount: int) -> bool:
            pass

        def give(self, resource: Resource, amount: int) -> None:
            pass

        def remove(self, resource: Resource, amount: int) -> None:
            self.give(resource, -amount)

        def fulfills_price(self, price: list[Price], in_trans=False) -> bool:
            merged_prices = defaultdict(lambda: 0)
            for p in price:
                if p.amount == 0:
                    continue
                merged_prices[p.resource] += p.amount

            with self.parent.Transaction(self.parent, in_trans):
                return all(self.has(key, value) for key, value in merged_prices.items())

        def gain(self, gain: list[Gain], in_trans=False) -> None:
            merged_gains = defaultdict(lambda: 0)
            for g in gain:
                if g.amount == 0:
                    continue
                merged_gains[g.resource] += g.amount

            with self.parent.Transaction(self.parent, in_trans):
                for key, value in merged_gains.items():
                    self.give(key, value)

        def pay_price(self, price: list[Price], in_trans=False) -> None:
            merged_price = defaultdict(lambda: 0)
            for p in price:
                if p.amount == 0:
                    continue
                merged_price[p.resource] += p.amount

            with self.parent.Transaction(self.parent, in_trans):
                for key, value in merged_price.items():
                    self.remove(key, value)

        def draw_card_raw(self) -> Creature:
            pass

        def reshuffle_discard(self) -> None:
            pass

        def draw_cards(self, N=1) -> tuple[int, bool]:
            cards_drawn = []
            discard_reshuffled = False
            for _ in range(N):
                if len(self.get_deck()) == 0:
                    self.reshuffle_discard()
                    discard_reshuffled = True

                    if len(self.get_deck()) == 0:
                        return cards_drawn, discard_reshuffled

                card = self.draw_card_raw()
                cards_drawn.append(card)

            return cards_drawn, discard_reshuffled

    class FreeCreature:

        def __init__(self, parent, guild_id: int, channel_id: int, message_id: int):
            self.parent = parent
            self.guild_id = guild_id
            self.channel_id = channel_id
            self.message_id = message_id
