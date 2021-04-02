import asyncio
import random

import registrator
import re
from blob import Context
from objects.constants.Modificators import Mods
from packets.Builder.index import PacketBuilder


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


mod_codes = {
    'NF': 1,
    'EZ': 2,
    'TD': 4,
    'HD': 8,
    'HR': 16,
    'SD': 32,
    'DT': 64,
    'RX': 128,
    'HT': 256,
    'NC': 576,
    'FL': 1024,
    'AT': 2048,
    'SO': 4096,
    'AP': 8192,
    'PF': 16416,
    'V2': 536870912
}
def string_to_mods(m: str) -> int:
    m = m.upper()
    mod_number = 0
    mods = re.findall(r".{1,2}", m)
    if not mods:
        return 0
    
    for mod in mods:
        mod_number += mod_codes.get(mod, 0)

    return mod_number


def humanize(value: int) -> str:
    return "{:,}".format(round(value)).replace(",", ".")


def random_hash() -> str:
    return '%032x' % random.getrandbits(128)


async def reload_settings() -> bool:
    # reload bancho settings
    await Context.load_bancho_settings()

    # reload default channels
    await registrator.load_default_channels()

    main_menu_packet = await PacketBuilder.MainMenuIcon(Context.bancho_settings['menu_icon'])
    channel_info_end = await PacketBuilder.ChannelListeningEnd()
    tasks = []
    for _, channel in Context.channels.items():
        if not channel.temp_channel and channel.can_read:
            tasks.append(PacketBuilder.ChannelAvailable(channel))

    channel_info_packets = await asyncio.gather(*tasks)

    for token in Context.players.get_all_tokens():
        token.enqueue(main_menu_packet + channel_info_end + b''.join(channel_info_packets))

    return True