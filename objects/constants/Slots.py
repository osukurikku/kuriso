from enum import IntFlag, unique


@unique
class SlotStatus(IntFlag):
    Open = 1
    Locked = 2
    NotReady = 4
    Ready = 8
    NoMap = 16
    Playing = 32
    Complete = 64
    HasPlayer = NotReady | Ready | NoMap | Playing | Complete
    Quit = 128


@unique
class SlotTeams(IntFlag):
    Neutral = 0
    Blue = 1
    Red = 2
