from src.core.base_types import StartCondition
from src.core.regions import *
from src.core.creatures import *

start_condition = StartCondition(
    {"region_recharge": 10, "creature_recharge": 10, "free_protection": 5, "free_expire": 60},
    [Village(), SmallMine()],
    [Commoner()],
    [Commoner() for i in range(10)],
)
