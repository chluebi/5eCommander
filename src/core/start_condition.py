from src.core.base_types import StartCondition
from src.core.regions import *
from src.core.creatures import *

start_condition = StartCondition(
    {}, [Village(), SmallMine()], [Commoner()], [Commoner() for i in range(10)]
)
