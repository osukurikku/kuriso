from typing import List, TypedDict

from objects.Multiplayer import Slot
from objects.constants.GameModes import GameModes
from objects.constants.IdleStatuses import Action
from objects.constants.Modificators import Mods
from objects.constants.multiplayer import (
    MatchTypes,
    MatchScoringTypes,
    MatchTeamTypes,
    MultiSpecialModes,
)


class TypedStatus(TypedDict):
    action: Action
    action_text: str
    map_md5: str
    mode: GameModes
    mods: Mods
    map_id: int


class TypedStats(TypedDict):
    total_score: int
    ranked_score: int
    pp: int
    accuracy: float
    total_plays: int
    playtime: int
    leaderboard_rank: int


class TypedPresence(TypedDict):
    action: int
    action_text: str
    map_md5: str
    mods: int
    mode: int
    map_id: int


class TypedReadMatch(TypedDict):
    match_type: MatchTypes
    mods: Mods
    name: str
    password: str
    beatmap_name: str
    beatmap_id: int
    beatmap_md5: str
    slots: List[Slot]
    host_id: int
    play_mode: GameModes
    scoring_type: MatchScoringTypes
    team_type: MatchTeamTypes
    match_freemod: MultiSpecialModes
    seed: int
