from enum import IntFlag, unique

# cmyui hey, how are you? Add me in friends in discord ;-;
__author__ = "cmyui"


@unique
class Mods(IntFlag):
    NoMod = 0
    NoFail = 1 << 0
    Easy = 1 << 1
    TouchDevice = 1 << 2
    Hidden = 1 << 3
    HardRock = 1 << 4
    SuddenDeath = 1 << 5
    DoubleTime = 1 << 6
    Relax = 1 << 7
    HalfTime = 1 << 8
    Nightcore = 1 << 9
    Flashlight = 1 << 10
    Autoplay = 1 << 11
    SpunOut = 1 << 12
    Relax2 = 1 << 13
    Perfect = 1 << 14
    Key4 = 1 << 15
    Key5 = 1 << 16
    Key6 = 1 << 17
    Key7 = 1 << 18
    Key8 = 1 << 19
    FadeIn = 1 << 20
    Random = 1 << 21
    Cinema = 1 << 22
    Target = 1 << 23
    Key9 = 1 << 24
    KeyCoop = 1 << 25
    Key1 = 1 << 26
    Key3 = 1 << 27
    Key2 = 1 << 28
    LastMod = 1 << 29  # can be named as ScoreV2 in last osu versions
    Mirror = 1 << 30
    KeyMod = Key1 | Key2 | Key3 | Key4 | Key5 | Key6 | Key7 | Key8 | Key9 | KeyCoop

    FreeModAllowed = (
        Hidden
        | HardRock
        | DoubleTime
        | Flashlight
        | FadeIn
        | Easy
        | Relax
        | Relax2
        | SpunOut
        | NoFail
        | Easy
        | HalfTime
        | Autoplay
        | KeyMod
        | Mirror
    )
    ScoreIncreaseMods = (
        Hidden
        | HardRock
        | DoubleTime
        | Flashlight
        | FadeIn
        | Easy
        | Relax
        | Relax2
        | SpunOut
        | NoFail
        | Easy
        | HalfTime
        | Autoplay
        | SuddenDeath
        | Perfect
        | KeyMod
        | Target
        | Random
        | Nightcore
        | LastMod
    )
    SpeedAltering = DoubleTime | Nightcore | HalfTime

    @staticmethod
    def filter_invalid_combos(m: "Mods") -> "Mods":
        """Remove any invalid mod combinations from and return `m`."""
        if m & (Mods.DoubleTime | Mods.Nightcore) and m & Mods.HalfTime:
            m &= ~Mods.HalfTime
        if m & Mods.Easy and m & Mods.HardRock:
            m &= ~Mods.HardRock
        if m & Mods.Relax and m & Mods.Relax2:
            m &= ~Mods.Autoplay
        if m & Mods.Perfect and m & Mods.SuddenDeath:
            m &= ~Mods.SuddenDeath

        return m
