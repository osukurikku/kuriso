from enum import IntFlag, unique


@unique
class MatchTypes(IntFlag):
    Standart = 0
    Powerplay = 1


@unique
class MatchScoringTypes(IntFlag):
    Score = 0
    Accuracy = 1
    Combo = 2
    ScoreV2 = 3


@unique
class MatchTeamTypes(IntFlag):
    HeadToHead = 0
    TagCoop = 1
    TeamVs = 2
    TagTeamVs = 3


@unique
class MultiSpecialModes(IntFlag):
    Empty = 0
    Freemod = 1
