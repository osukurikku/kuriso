import json
import math
import random
from typing import List, TYPE_CHECKING

import aiohttp

from blob import Context
from bot.bot import CrystalBot
from config import Config
from helpers import new_utils
from objects.constants import Privileges, Countries
from objects.constants.GameModes import GameModes

if TYPE_CHECKING:
    from objects.Player import Player


@CrystalBot.register_command("!help", aliases=["!h"])
async def test_command(*_):
    return "Click (here)[https://kurikku.pw/index.php?p=16&id=4] for the full command list"


@CrystalBot.register_command("!roll")
async def roll(args: List[str], player: "Player", _):
    max_points = 100
    if args:
        if args[0].isdigit() and int(args[0]) > 0:
            max_points = int(args[0])

    points = random.randint(0, max_points)
    return f"{player.name} rolls {points} poins!"


@CrystalBot.register_command("!recommend", aliases=["!rec"])
async def recommend(args: List[str], player: "Player", __):
    stats = player.stats[GameModes.STD]

    mods = -1
    if args:
        mods = new_utils.string_to_mods("".join(args))

    params = {"pp": stats.pp, "token": Config.config["pprapi_token"]}

    if mods > -1:
        params["mods"] = mods

    data = None
    async with aiohttp.ClientSession() as sess:
        async with sess.get(
            "https://api.kotrik.ru/api/recommendMap", params=params, timeout=5
        ) as resp:
            try:
                data = await resp.json(content_type=None)
            finally:
                pass

    if not data or not data["code"] != 200:
        return "At the moment, I can't recommend anything, try later!"

    readable_mods = new_utils.readable_mods(data["m"])
    # pylint: disable=consider-using-f-string
    format_result = "[http://osu.kurikku.pw/b/{bid} {art} - {name} [{diff}]] Stars: {stars} | BPM: {bpm} | Length: {length} | PP: {pps} {mods}".format(
        bid=data["b"],
        art=data["art"],
        name=data["t"],
        diff=data["v"],
        stars=data["d"],
        bpm=data["bpm"],
        length=f"{math.floor(data['l'] / 60)}:{str(data['l'] % 60)}",
        pps=data["pp99"],
        mods=f"+{readable_mods}",
    )

    return format_result


@CrystalBot.register_command("!stats", aliases=["!st"])
async def user_stats(args: List[str], player: "Player", _):
    mode = GameModes(0)
    if len(args) < 1:
        nickname = player.name
    else:
        nickname = args[0]

    if len(args) > 1 and args[1].isdigit():
        mode = GameModes(int(args[1]))

    if mode > 3:
        return "GameMode is incorrect"

    token = Context.players.get_token(name=nickname.lower())
    if not token:
        return "Player not online"

    mode_str = GameModes.resolve_to_str(mode)
    stats = token.stats[mode]

    # pylint: disable=consider-using-f-string
    acc = "{0:.2f}%".format(stats.accuracy)
    return (
        f"User: {nickname}\n"
        f"ID: {token.id}\n"
        "---------------------\n"
        f"Stats for {mode_str} #{stats.leaderboard_rank}\n"
        f"Ranked score: {new_utils.humanize(stats.ranked_score)}\n"
        f"Accuracy: {acc}\n"
        f"Play count: {new_utils.humanize(stats.total_plays)}\n"
        f"Total score: {new_utils.humanize(stats.total_score)}\n"
        f"PP count: {new_utils.humanize(stats.pp)}"
    )


@CrystalBot.register_command("!flag")
@CrystalBot.check_perms(need_perms=Privileges.USER_DONOR)
async def flag_change_donor(args: List[str], player: "Player", _):
    if not args:
        return "Enter country in ISO format. Google it, if you dont know what is this"

    flag = Countries.get_country_id(args[0].upper())
    if not flag:
        return "Unknowing flag"

    await Context.mysql.execute(
        "UPDATE users_stats SET country = %s WHERE id = %s",
        [args[0].upper(), player.id],
    )

    await player.parse_country(player.ip)
    return "Your flag is changed"


@CrystalBot.register_command("!clantop")
async def clantop(args: List[str], player: "Player", _):
    if not args:
        return "Enter in format: <on/off>"

    status = args[0].lower() == "on"

    user_settings = await Context.redis.get(f"kr:user_settings:{player.id}")
    if not user_settings:
        user_settings = {"clan_top_enabled": status}
    else:
        user_settings = json.loads(user_settings.decode())
        user_settings["clan_top_enabled"] = status

    await Context.redis.set(f"kr:user_settings:{player.id}", json.dumps(user_settings))
    return f"Okay, you switch this feature to: {status}. This feature replace Top Country to Top Clans"
