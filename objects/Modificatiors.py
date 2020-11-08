from enum import IntFlag, unique

# cmyui hey, how are you? Add me in friends in discord ;-;
__author__ = "cmyui"


@unique
class Modifications(IntFlag):
    NOMOD = 0
    NOFAIL = 1 << 0
    EASY = 1 << 1
    TOUCHSCREEN = 1 << 2  # old: 'NOVIDEO'
    HIDDEN = 1 << 3
    HARDROCK = 1 << 4
    SUDDENDEATH = 1 << 5
    DOUBLETIME = 1 << 6
    RELAX = 1 << 7
    HALFTIME = 1 << 8
    NIGHTCORE = 1 << 9
    FLASHLIGHT = 1 << 10
    AUTOPLAY = 1 << 11
    SPUNOUT = 1 << 12
    AUTOPILOT = 1 << 13
    PERFECT = 1 << 14
    KEY4 = 1 << 15
    KEY5 = 1 << 16
    KEY6 = 1 << 17
    KEY7 = 1 << 18
    KEY8 = 1 << 19
    FADEIN = 1 << 20
    RANDOM = 1 << 21
    CINEMA = 1 << 22
    TARGET = 1 << 23
    KEY9 = 1 << 24
    KEYCOOP = 1 << 25
    KEY1 = 1 << 26
    KEY3 = 1 << 27
    KEY2 = 1 << 28
    SCOREV2 = 1 << 29
    MIRROR = 1 << 30

    @staticmethod
    def filter_invalid_combos(m: 'Modifications') -> 'Modifications':
        """Remove any invalid mod combinations from and return `m`."""
        if m & (Modifications.DOUBLETIME | Modifications.NIGHTCORE) and m & Modifications.HALFTIME:
            m &= ~Modifications.HALFTIME
        if m & Modifications.EASY and m & Modifications.HARDROCK:
            m &= ~Modifications.HARDROCK
        if m & Modifications.RELAX and m & Modifications.AUTOPILOT:
            m &= ~Modifications.AUTOPILOT
        if m & Modifications.PERFECT and m & Modifications.SUDDENDEATH:
            m &= ~Modifications.SUDDENDEATH

        return m
