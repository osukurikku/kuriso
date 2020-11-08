from enum import IntEnum, unique


@unique
class Action(IntEnum):
    Idle = 0
    Afk = 1
    Playing = 2
    Editing = 3
    Modding = 4
    Multiplayer = 5
    Watching = 6
    Unknown = 7
    Testing = 8
    Submitting = 9
    Paused = 10
    Lobby = 11
    Multiplayer_play = 12
    OsuDirect = 13
