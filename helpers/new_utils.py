from objects.constants.Modificators import Mods


def readable_mods(m: Mods) -> str:
    """
        Return a string with readable std mods.
        Used to convert a mods number for oppai
    """
    r = ""
    if m == 0:
        return "NoMod"
    if m & Mods.NoFail:
        r += "NF"
    if m & Mods.Easy:
        r += "EZ"
    if m & Mods.Hidden:
        r += "HD"
    if m & Mods.HardRock:
        r += "HR"
    if m & Mods.DoubleTime:
        r += "DT"
    if m & Mods.HalfTime:
        r += "HT"
    if m & Mods.Flashlight:
        r += "FL"
    if m & Mods.SpunOut:
        r += "SO"
    if m & Mods.TouchDevice:
        r += "TD"
    if m & Mods.Relax:
        r += "RX"
    if m & Mods.Relax2:
        r += "AP"
    return r


def humanize(value: int) -> str:
    return "{:,}".format(round(value)).replace(",", ".")
