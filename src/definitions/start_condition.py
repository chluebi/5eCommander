from src.database.database import Database
from src.definitions.regions import *
from src.definitions.creatures import *

start_condition = Database.StartCondition(
    {
        "max_orders": 5,
        "order_recharge": 5,
        "max_magic": 10,
        "magic_recharge": 10,
        "max_cards": 10,
        "card_recharge": 3,
        "region_recharge": 10,
        "creature_recharge": 10,
        "free_protection": 5,
        "free_expire": 60,
    },
    [Village(), SmallMine()],
    [Commoner()],
    [Commoner() for i in range(10)],
)
