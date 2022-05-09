import math
import os
import time

import psutil

from blob import Context
from objects.constants.GameModes import GameModes
from objects.constants.Modificators import Mods


def getSystemInfo():
    """
    Legacy system info
    """
    data = {
        "unix": os.name == "posix",
        "connectedUsers": len(Context.players.get_all_tokens(ignore_tournament_clients=True)),
        "matches": len(Context.matches.items()),
    }

    # General stats
    delta = time.time() - Context.start_time
    days = math.floor(delta / 86400)
    delta -= days * 86400

    hours = math.floor(delta / 3600)
    delta -= hours * 3600

    minutes = math.floor(delta / 60)
    delta -= minutes * 60

    seconds = math.floor(delta)

    data["uptime"] = f"{days}d {hours}h {minutes}m {seconds}s"
    data["cpuUsage"] = psutil.cpu_percent()
    memory = psutil.virtual_memory()

    # Unix only stats
    if data["unix"]:
        data["loadAverage"] = os.getloadavg()
        # pylint: disable=consider-using-f-string
        data["totalMemory"] = f"{memory.total / 1074000000:.2f}"
        # pylint: disable=consider-using-f-string
        data["usedMemory"] = f"{memory.active / 1074000000:.2f}"
    else:
        data["loadAverage"] = (0, 0, 0)
        data["totalMemory"] = "0"
        data["usedMemory"] = "sorry u're run it on windowS!"

    return data


def getRank(
    game_mode: GameModes = None,
    mods: Mods = None,
    acc: float = None,
    c300: int = None,
    c100: int = None,
    c50: int = None,
    cmiss: int = None,
):
    """
    Return a string with rank/grade for a given score.
    Used mainly for tillerino
    """
    total = c300 + c100 + c50 + cmiss
    hdfl = (mods & Mods.Hidden > 0) or (mods & Mods.Flashlight > 0)

    def ss():
        return "XH" if hdfl else "X"

    def s():
        return "SH" if hdfl else "S"

    rank = "A"
    if game_mode == GameModes.STD:
        # osu!std
        if acc == 100:
            rank = ss()
        if c300 / total > 0.90 and c50 / total < 0.1 and cmiss == 0:
            rank = s()
        if (c300 / total > 0.80 and cmiss == 0) or (c300 / total > 0.90):
            rank = "A"
        if (c300 / total > 0.70 and cmiss == 0) or (c300 / total > 0.80):
            rank = "B"
        if c300 / total > 0.60:
            rank = "C"
        rank = "D"
    elif game_mode == GameModes.TAIKO:
        # TODO: taiko rank
        # TODO: TF?
        rank = "A"
    elif game_mode == GameModes.CTB:
        # CtB
        if acc == 100:
            rank = ss()
        if 98.01 <= acc <= 99.99:
            rank = s()
        if 94.01 <= acc <= 98.00:
            rank = "A"
        if 90.01 <= acc <= 94.00:
            rank = "B"
        if 98.01 <= acc <= 90.00:
            rank = "C"
        rank = "D"
    elif game_mode == GameModes.MANIA:
        # osu!mania
        if acc == 100:
            rank = ss()
        if acc > 95:
            rank = s()
        if acc > 90:
            rank = "A"
        if acc > 80:
            rank = "B"
        if acc > 70:
            rank = "C"
        rank = "D"

    return rank
