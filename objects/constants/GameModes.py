from enum import IntEnum, unique


@unique
class GameModes(IntEnum):
    STD = 0
    TAIKO = 1
    CTB = 2
    MANIA = 3

    @staticmethod
    def resolve_to_str(m: "GameModes") -> str:
        mods = {m.STD: "std", m.TAIKO: "taiko", m.CTB: "ctb", m.MANIA: "mania"}
        return mods.get(m, None)
