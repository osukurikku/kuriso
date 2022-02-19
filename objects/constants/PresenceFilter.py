from enum import IntEnum, unique


@unique
class PresenceFilter(IntEnum):
    Nobody = 0
    All = 1
    Friends = 2
