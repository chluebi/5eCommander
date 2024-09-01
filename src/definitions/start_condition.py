from typing import Optional
from src.database.database import Database
from src.core.base_types import Resource, Gain
from src.definitions.regions import *
from src.definitions.creatures import *


def join_action(player_db: Database.Player, con: Optional[Database.TransactionManager]) -> None:
    with player_db.parent.transaction(parent=con) as con:
        player_db.gain(
            [Gain(Resource.ORDERS, 4), Gain(Resource.GOLD, 2), Gain(Resource.RALLY, 3)], con=con
        )
        player_db.draw_cards(N=5, con=con)


start_condition = Database.StartCondition(
    {
        "channel_id": 0,
        "max_orders": 5,
        "order_recharge": 3 * 3600,
        "max_magic": 10,
        "magic_recharge": 1 * 3600,
        "max_cards": 10,
        "card_recharge": 2 * 3600,
        "region_recharge": 3600,
        "creature_recharge": 12 * 3600,
        "free_protection": 120,
        "free_expire": 2 * 24 * 3600,
        "conflict_duration": 24 * 3600,
    },
    [
        RoyalGift(),
        CourtPolitics(),
        Delegation(),
        ArtefactFence(),
        Collections(),
        Laborers(),
        Cave(),
        Dungeon(),
        HiddenLair(),
        Ritual(),
        Library(),
        BindingSpell(),
        HiddenCache(),
        Hunt(),
        Abandon(),
    ],
    [
        Servant(),
        Commoner(),
        NoviceAdventurer(),
        NoviceMage(),
        LoyalSquire(),
        Herald(),
        Local(),
        Guide(),
        MagicStudent(),
        Farmer(),
        Ambassador(),
        Trader(),
        Explorer(),
        Mentor(),
        Hunter(),
        Messenger(),
        Towncrier(),
        Quartermaster(),
        ArcaneTutor(),
        Druid(),
        RetiredGeneral(),
        SwordSmith(),
        Scout(),
        Librarian(),
        Nymph(),
        Soldier(),
        Bandit(),
        Paladin(),
        ArcaneGolem(),
        WildDrake(),
        Duke(),
        Spy(),
        Drow(),
        Alchemist(),
        TalkingCat(),
        Tavernkeeper(),
        Mimic(),
        GreatArcaneWyrm(),
        RedDragon(),
        Saboteur(),
    ],
    [
        Servant(),
        Servant(),
        Commoner(),
        Commoner(),
        Commoner(),
        NoviceAdventurer(),
        NoviceAdventurer(),
        NoviceMage(),
        LoyalSquire(),
    ],
    join_action,
)
