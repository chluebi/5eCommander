import time

from src.core.creatures import *
from src.core.regions import *


def test_text():
    commoner = Commoner()

    assert commoner.quest_ability_effect_text() == ""
    assert commoner.campaign_ability_effect_text() == "gain 1 🚩rally"

    village = Village()

    assert village.quest_effect_text() == "gain 1 ⚒️worker"

    small_mine = SmallMine()

    assert small_mine.quest_effect_text() == "pay 5 🪙gold -> gain 1 ⚒️worker"
