from src.database.database import Database
from src.definitions.regions import *
from src.definitions.creatures import *

start_condition = Database.StartCondition(
    {
        "channel_id": 0,
        "max_orders": 3,
        "order_recharge": 30,
        "max_magic": 10,
        "magic_recharge": 30,
        "max_cards": 10,
        "card_recharge": 30,
        "region_recharge": 10,
        "creature_recharge": 10,
        "free_protection": 30,
        "free_expire": 180,
    },
    [Village(), SmallMine()],
    [Commoner()],
    [Commoner() for i in range(10)],
)
