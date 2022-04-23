import re
from typing import List, TYPE_CHECKING, Any, Dict, Union

import aiohttp
import traceback
from sentry_sdk import capture_exception

from blob import Context
from bot.bot import CrystalBot
from helpers import new_utils, legacy_utils
from objects.constants.GameModes import GameModes
from objects.constants.KurikkuPrivileges import KurikkuPrivileges
from objects.constants.Modificators import Mods

if TYPE_CHECKING:
    from objects.Player import Player
    from objects.BanchoObjects import Message

NP_REGEX = re.compile(r"(^https?:\/\/.*(\/b\/|\/beatmapsets\/\d*\#(?:.+?\/)?))(?:\/?)(\d*)")
ALLOWED_MODS = [
    "NO",
    "NF",
    "EZ",
    "HD",
    "HR",
    "DT",
    "HT",
    "NC",
    "FL",
    "SO",
    "AP",
    "RX",
]
ALLOWED_MODS_MAPPING = {
    "NO": Mods.NoMod,
    "NF": Mods.NoFail,
    "EZ": Mods.Easy,
    "HD": Mods.Hidden,
    "HR": Mods.HardRock,
    "DT": Mods.DoubleTime,
    "HT": Mods.HalfTime,
    "NC": Mods.Nightcore,
    "FL": Mods.Flashlight,
    "SO": Mods.SpunOut,
    "AP": Mods.Relax2,
    "RX": Mods.Relax,
}

# pylint: disable=consider-using-f-string
async def get_pp_message(
    token: "Player", just_data: bool = False
) -> Union[str, Dict[Any, Any]]:
    currentMap = token.tillerino[0]
    currentMods = token.tillerino[1]
    currentAcc = token.tillerino[2]

    params = {"b": currentMap, "m": currentMods.value, "a": str(currentAcc)}

    data = None
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(
                "http://127.0.0.1:5002/api/v1/pp", params=params, timeout=10
            ) as resp:
                try:
                    data = await resp.json()
                finally:
                    pass
    except Exception as e:
        capture_exception(e)
        traceback.print_exc()
        return "LETS api is down. Try later!"

    if "status" not in data:
        return "Unknown error in LETS API call. Try later!"

    if data["status"] != 200:
        return (
            f'Error in LETS API call ({data["message"]})'
            if "message" in data
            else "Unknown error in LETS API call. Try later!"
        )

    if just_data:
        return data

    msg = f'{data["song_name"]} {"+" if currentMods > 0 else ""}{new_utils.readable_mods(currentMods)} '
    if currentAcc > -1.0:
        msg += f"{int(currentAcc)}%: {data['pp'][0]}"
    else:
        msg += f'95%: {data["pp"][3]}pp | 98%: {data["pp"][2]}pp | 99% {data["pp"][1]}pp | 100%: {data["pp"][0]}pp'

    original_ar = data["ar"]
    # calc new AR if HR/EZ is on
    if currentMods & Mods.Easy:
        data["ar"] = max(0, data["ar"] / 2)
    if currentMods & Mods.HardRock:
        data["ar"] = min(10, data["ar"] * 1.4)

    ar_to_msg = "({})".format(original_ar) if original_ar != data["ar"] else ""

    msg += (
        f' | {data["bpm"]} BPM | AR {data["ar"]}{ar_to_msg} | {round(data["stars"], 2)} stars'
    )

    return msg


@CrystalBot.register_command(
    "\x01ACTION is listening to",
    aliases=["\x01ACTION is playing", "\x01ACTION is watching"],
)
async def tilleino_like(args: List[str], token: "Player", message: "Message"):
    if (
        message.to.startswith("#")
        and (token.privileges & KurikkuPrivileges.Donor) != KurikkuPrivileges.Donor
    ):
        return False  # don't allow run np commands in public channels!

    play_or_watch = "playing" in message.body or "watching" in message.body
    # Get URL from message
    beatmap_url = args[0][1:]
    modsEnum = Mods(0)
    if play_or_watch:
        mapping = {
            "-Easy": Mods.Easy,
            "-NoFail": Mods.NoFail,
            "+Hidden": Mods.Hidden,
            "+HardRock": Mods.HardRock,
            "+Nightcore": Mods.Nightcore,
            "+DoubleTime": Mods.DoubleTime,
            "-HalfTime": Mods.HalfTime,
            "+Flashlight": Mods.Flashlight,
            "-SpunOut": Mods.SpunOut,
        }
        for part in args:
            part = part.replace("\x01", "")
            if part in mapping:
                modsEnum |= mapping[part]
    try:
        beatmap_id = NP_REGEX.search(beatmap_url).groups(3)[2]
    except Exception as e:
        traceback.print_exc()
        capture_exception(e)
        return "Can't find beatmap"

    token.tillerino = [int(beatmap_id), modsEnum, -1.0]

    return await get_pp_message(token)


@CrystalBot.register_command("!with")
async def tillerino_mods(args: List[str], token: "Player", message: "Message"):
    if not args:
        return "Enter mods as first argument"

    if (
        message.to.startswith("#")
        and (token.privileges & KurikkuPrivileges.Donor) != KurikkuPrivileges.Donor
    ):
        return False  # don't allow run np commands in public channels!

    if token.tillerino[0] == 0:
        return "Please give me beatmap first with /np command"

    mods_list = [a.upper() for a in args]
    mods_enum = Mods(0)
    for mod in mods_list:
        if mod not in ALLOWED_MODS:
            return f"Invalid mods. Allowed mods: {', '.join(ALLOWED_MODS)}. Make sure that you separate them."

        mods_enum |= ALLOWED_MODS_MAPPING.get(mod, 0)

    token.tillerino[1] = mods_enum

    return await get_pp_message(token)


@CrystalBot.register_command("!acc")
async def tillerino_acc(args: List[str], token: "Player", message: "Message"):
    if not args:
        return "Enter mods as first argument"

    if (
        message.to.startswith("#")
        and (token.privileges & KurikkuPrivileges.Donor) != KurikkuPrivileges.Donor
    ):
        return False  # don't allow run np commands in public channels!

    if token.tillerino[0] == 0:
        return "Please give me beatmap first with /np command"

    try:
        acc = float(args[0])
    except Exception:
        return "Please enter proper accuracy"

    token.tillerino[2] = acc
    return await get_pp_message(token)


@CrystalBot.register_command("!last")
async def tillerino_last(_, token: "Player", message: "Message"):
    if (
        message.to.startswith("#")
        and (token.privileges & KurikkuPrivileges.Donor) != KurikkuPrivileges.Donor
    ):
        return False  # don't allow run np commands in public channels!

    data = await Context.mysql.fetch_one(
        """SELECT beatmaps.song_name as sn, scores.*,
        beatmaps.beatmap_id as bid, beatmaps.difficulty_std, beatmaps.difficulty_taiko, beatmaps.difficulty_ctb,
        beatmaps.difficulty_mania, beatmaps.max_combo as fc
    FROM scores
    LEFT JOIN beatmaps ON beatmaps.beatmap_md5=scores.beatmap_md5
    WHERE scores.userid = :id
    ORDER BY scores.time DESC
    LIMIT 1""",
        {"id": token.id},
    )

    diffString = f"difficulty_{GameModes.resolve_to_str(GameModes(data['play_mode']))}"
    rank = legacy_utils.getRank(
        data["play_mode"],
        data["mods"],
        data["accuracy"],
        data["300_count"],
        data["100_count"],
        data["50_count"],
        data["misses_count"],
    )

    ifPlayer = f"{token.name if message.to != CrystalBot.bot_name else ''} | "
    ifFc = (
        " (FC)" if data["max_combo"] == data["fc"] else f" {data['max_combo']}x/{data['fc']}x"
    )
    beatmapLink = f"[http://osu.ppy.sh/b/{data['bid']} {data['sn']}]"

    hasPP = data["play_mode"] != GameModes.CTB.value

    msg = ifPlayer
    msg += beatmapLink
    if data["play_mode"] != GameModes.STD.value:
        msg += f" <{GameModes.resolve_to_str(GameModes(data['play_mode']))}>"

    if data["mods"]:
        msg += " +" + new_utils.readable_mods(Mods(data["mods"]))

    if not hasPP:
        msg += " | {0:,}".format(data["score"])
        msg += ifFc
        msg += f" | {round(data['accuracy'], 2)}%, {rank.upper()}"
        msg += f" {{ {data['300_count']} / {data['100_count']} / {data['50_count']} / {data['misses_count']} }}"
        msg += f" | {round(data[diffString], 2)} stars"
        return msg

    msg += f" | {round(data['accuracy'], 2)}%, {rank.upper()}"
    msg += ifFc
    msg += f" | {round(data['pp'], 2)}pp"

    stars = data[diffString]
    if data["mods"]:
        token.tillerino[0] = data["bid"]
        token.tillerino[1] = Mods(data["mods"])
        peace_data = await get_pp_message(token, just_data=True)
        if "stars" in peace_data:
            stars = peace_data["stars"]

    msg += " | {0:.2f} stars".format(stars)
    return msg
