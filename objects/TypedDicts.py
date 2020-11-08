from typing_extensions import TypedDict

from objects.constants.GameModes import GameModes
from objects.constants.IdleStatuses import Action
from objects.constants.Modificatiors import Modifications


class TypedStatus(TypedDict):
    action: Action
    action_text: str
    map_md5: str
    mode: GameModes
    mods: Modifications
    map_id: int


class TypedStats(TypedDict):
    total_score: int
    ranked_score: int
    pp: int
    accuracy: float
    total_plays: int
    playtime: int
    leaderboard_rank: int
