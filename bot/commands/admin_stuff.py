import asyncio
from typing import List, TYPE_CHECKING

import aiohttp

from blob import Context
from bot.bot import CrystalBot
from config import Config
from helpers import userHelper, legacy_utils, new_utils
from lib import logger
from objects.constants import Privileges
from objects.constants.BanchoRanks import BanchoRanks
from objects.constants.KurikkuPrivileges import KurikkuPrivileges
from packets.Builder.index import PacketBuilder

if TYPE_CHECKING:
    from objects.Player import Player


@CrystalBot.register_command("!alert")
@CrystalBot.check_perms(need_perms=KurikkuPrivileges.CM)
async def alert(args: List[str], *_):
    if not args:
        return "What do you wanna to say?"

    notify_packet = PacketBuilder.Notification(" ".join(args))
    for user in Context.players.get_all_tokens(ignore_tournament_clients=True):
        user.enqueue(notify_packet)

    return "Await your msg!"


@CrystalBot.register_command("!useralert", aliases=["!alertuser"])
@CrystalBot.check_perms(need_perms=KurikkuPrivileges.CM)
async def user_alert(args: List[str], *_):
    if args:
        if len(args) < 2:
            return "What do you wanna to say?"
    else:
        return "Who do you want to write to?"

    name = args[0].lower()
    text = " ".join(args[1:])

    to_token = Context.players.get_token(name=name)
    if not to_token:
        return "User not found"

    notify_packet = PacketBuilder.Notification(text)
    to_token.enqueue(notify_packet)
    return "Message was sent"


@CrystalBot.register_command("!kickall")
@CrystalBot.check_perms(need_perms=KurikkuPrivileges.CM)
async def kick_all(*_):
    tasks = []
    for user in Context.players.get_all_tokens():
        if user.is_admin:
            continue

        tasks.append(user.kick())

    await asyncio.gather(*tasks)
    return "All kicked!"


@CrystalBot.register_command("!kick")
@CrystalBot.check_perms(need_perms=KurikkuPrivileges.CM)
async def kick(args: List[str], *_):
    if not args:
        return "Who do you want to kick?"

    username = args[0]
    if len(args) > 1:
        username = "_".join(args).lower()

    to_token = Context.players.get_token(name=username)
    if not to_token:
        return "User not found"

    if to_token.is_admin:
        return "User is admin, you can't kick him"

    await to_token.kick()
    return "User kicked successfully"


@CrystalBot.register_command("!silence")
@CrystalBot.check_perms(need_perms=KurikkuPrivileges.ChatMod)
async def silence(args: List[str], player: "Player", _):
    if args:
        if len(args) < 2:
            return "You need put amount"
        if len(args) < 3 or args[2].lower() not in ["s", "m", "h", "d"]:
            return "You need to set unit s/m/h/d"
        if len(args) < 4:
            return "You need to put reason"
    else:
        return "I need nickname who you want to silence"

    target = args[0]
    amount = args[1]
    unit = args[2]
    reason = " ".join(args[3:]).strip()
    if not amount.isdigit():
        return "The amount must be a number."

    # Calculate silence seconds
    silenceTime = {
        "s": int(amount),
        "m": int(amount) * 60,
        "h": int(amount) * 3600,
        "d": int(amount) * 86400,
    }[unit]

    # Max silence time is 7 days
    if silenceTime > 604800:
        return "Invalid silence time. Max silence time is 7 days."

    if to_token := Context.players.get_token(name=target.lower()):
        if to_token.id == player.id or to_token.privileges >= player.privileges:
            return "You can't silence that dude"

        await to_token.silence(silenceTime, reason, player.id)
        logger.klog(f"<Player/{to_token.name}has been silenced for following reason: {reason}")
        return "User silenced"

    offline_user = await userHelper.get_start_user(target.lower())
    if offline_user["privileges"] > player.privileges:
        return "You can't silence that dude"

    if not offline_user:
        return "User not found!"

    res = await userHelper.silence(offline_user["id"], silenceTime, reason, player.id)
    if not res:
        return "Not silenced!"

    logger.klog(
        f"<Player/{offline_user['username']}> has been silenced for following reason: {reason}",
    )
    return "User successfully silenced"


@CrystalBot.register_command("!removesilence")
@CrystalBot.check_perms(need_perms=KurikkuPrivileges.ChatMod)
async def remove_silence(args: List[str], player: "Player", _):
    if not args:
        return "I need nickname who you want to remove the silence"

    target = args[0]

    if to_token := Context.players.get_token(name=target.lower()):
        logger.klog(f"<Player/{to_token.name}> silence reset")
        await to_token.silence(0, "", player.id)
        return "User silence is removed"

    offline_user = await userHelper.get_start_user(target.lower())
    if not offline_user:
        return "User not found!"

    res = await userHelper.silence(offline_user["id"], 0, "", player.id)
    if not res:
        return "Not silenced!"

    logger.klog(f"<Player/{offline_user['username']}> silence reset")
    return "User successfully silenced"


@CrystalBot.register_command("!ban")
@CrystalBot.check_perms(need_perms=Privileges.ADMIN_BAN_USERS)
async def ban(args: List[str], player: "Player", _):
    if not args:
        return "Which player should be banned?"

    offline_user = await userHelper.get_start_user(args[0].lower())
    if not offline_user:
        return "Player not found"

    if offline_user["privileges"] > player.privileges:
        return "You can't silence that dude"

    await userHelper.ban(offline_user["id"])

    # send packet to user if he's online
    if to_token := Context.players.get_token(name=args[0].lower()):
        to_token.enqueue(PacketBuilder.UserID(-1))

    if Config.config["crystalbot_api"]:
        params = {
            "token": Config.config["crystalbot_token"],
            "banned": offline_user["username"],
            "type": 1,
            "author": player.name,
        }
        async with aiohttp.ClientSession() as sess:
            async with sess.get(
                f'{Config.config["crystalbot_api"]}api/v1/submitBanOrRestrict',
                params=params,
            ):
                pass  # just send it and nothing more ;d

    await userHelper.log_rap(player.id, f'has banned {offline_user["username"]}')
    return "Player has been banned"


@CrystalBot.register_command("!lock")
@CrystalBot.check_perms(need_perms=Privileges.ADMIN_BAN_USERS)
async def lock(args: List[str], player: "Player", _):
    if not args:
        return "Which player should be locked?"

    to_token = Context.players.get_token(name=args[0].lower())
    if not to_token:
        return "Player not found"

    if to_token.privileges > player.privileges:
        return "You can't touch this player"

    to_token.enqueue(PacketBuilder.UserID(-3))  # ban client id
    return "Player's client has been locked"


@CrystalBot.register_command("!unban")
@CrystalBot.check_perms(need_perms=Privileges.ADMIN_BAN_USERS)
async def unban(args: List[str], player: "Player", _):
    if not args:
        return "Which player should unbanned?"

    offline_user = await userHelper.get_start_user(args[0].lower())
    if not offline_user:
        return "User not found!"

    await userHelper.unban(offline_user["id"])

    if Config.config["crystalbot_api"]:
        params = {
            "token": Config.config["crystalbot_token"],
            "banned": offline_user["username"],
            "type": 3,
            "author": player.name,
        }
        async with aiohttp.ClientSession() as sess:
            async with sess.get(
                f'{Config.config["crystalbot_api"]}api/v1/submitBanOrRestrict',
                params=params,
            ):
                pass  # just send it and nothing more ;d

    await userHelper.log_rap(player.id, f'has unbanned {offline_user["username"]}')
    return f'Welcome back {offline_user["username"]}'


@CrystalBot.register_command("!restrict")
@CrystalBot.check_perms(need_perms=Privileges.ADMIN_BAN_USERS)
async def restrict(args: List[str], player: "Player", _):
    if not args:
        return "Which player should be restricted?"

    offline_user = await userHelper.get_start_user(args[0].lower())
    if not offline_user:
        return "Player not found"

    if offline_user["privileges"] > player.privileges:
        return "You can't silence that dude"

    await userHelper.restrict(offline_user["id"])

    # send packet to user if he's online
    if to_token := Context.players.get_token(name=args[0].lower()):
        to_token.privileges &= ~Privileges.USER_PUBLIC
        to_token.enqueue(PacketBuilder.UserRestricted())
        await CrystalBot.ez_message(
            args[0].lower(),
            "Your account is currently in restricted mode. Please visit kurikku's website for more information.",
        )

    if Config.config["crystalbot_api"]:
        params = {
            "token": Config.config["crystalbot_token"],
            "banned": offline_user["username"],
            "type": 0,
            "author": player.name,
        }
        async with aiohttp.ClientSession() as sess:
            async with sess.get(
                f'{Config.config["crystalbot_api"]}api/v1/submitBanOrRestrict',
                params=params,
            ):
                pass  # just send it and nothing more ;d

    await userHelper.log_rap(player.id, f'has restricted {offline_user["username"]}')
    return "Player has been restricted"


@CrystalBot.register_command("!unrestrict")
@CrystalBot.check_perms(need_perms=Privileges.ADMIN_BAN_USERS)
async def unrestrict(args: List[str], player: "Player", _):
    if not args:
        return "Which player should unrestricted?"

    offline_user = await userHelper.get_start_user(args[0].lower())
    if not offline_user:
        return "User not found!"

    await userHelper.unban(offline_user["id"])
    if to_token := Context.players.get_token(uid=offline_user["id"]):
        await to_token.logout()  # just update him privileges

    if Config.config["crystalbot_api"]:
        params = {
            "token": Config.config["crystalbot_token"],
            "banned": offline_user["username"],
            "type": 2,
            "author": player.name,
        }
        async with aiohttp.ClientSession() as sess:
            async with sess.get(
                f'{Config.config["crystalbot_api"]}api/v1/submitBanOrRestrict',
                params=params,
            ):
                pass  # just send it and nothing more ;d

    await userHelper.log_rap(player.id, f'has unrestricted {offline_user["username"]}')
    return f'Welcome back {offline_user["username"]}'


async def system_reload():
    await new_utils.reload_settings()

    return "Settings reloaded!"


async def system_maintenance(maintenance: bool = False) -> str:
    Context.bancho_settings["bancho_maintenance"] = maintenance
    await Context.mysql.execute(
        "UPDATE bancho_settings SET value_int = :maintenance WHERE name = 'bancho_maintenance'",
        {"maintenance": int(maintenance)},
    )

    force_disconnect = PacketBuilder.UserID(-5)
    maintenance_packet = PacketBuilder.Notification(
        "Our bancho server is in maintenance mode. Please try to login again later.",
    )

    if maintenance:
        for user in Context.players.get_all_tokens(ignore_tournament_clients=True):
            user.enqueue(maintenance_packet)
            if not user.is_admin:
                user.enqueue(force_disconnect)
                await user.logout()

        return "The server is now in maintenance mode!"

    return "The server is no longer in maintenance mode!"


async def system_status():
    data = legacy_utils.getSystemInfo()

    # Final message
    lets_version = await Context.redis.get("lets:version")
    if not lets_version:
        lets_version = "unknown version"

    msg = f"kuriso server v{Context.version}\n"
    msg += f"LETS scores server v{lets_version}\n"
    msg += "made by the Kurikku team\n"
    msg += "\n"
    msg += "=== KURISO STATS ===\n"
    msg += f"Connected users: {data['connectedUsers']}\n"
    msg += f"Multiplayer matches: {data['matches']}\n"
    msg += f"Uptime: {data['uptime']}\n"
    msg += "\n"
    msg += "=== SYSTEM STATS ===\n"
    msg += f"CPU: {data['cpuUsage']}%\n"
    msg += f"RAM: {data['usedMemory']}GB/{data['totalMemory']}GB\n"
    if data["unix"]:
        load_average = data["loadAverage"]
        msg += f"Load average: {load_average[0]}/{load_average[1]}/{load_average[2]}\n"

    return msg


@CrystalBot.register_command("!system")
@CrystalBot.check_perms(need_perms=Privileges.ADMIN_MANAGE_SERVERS)
async def system_commands(args: List[str], *_):
    if not args:
        return "Use it like !system [maintenance/restart]"

    additional_context = args[0]
    if additional_context == "maintenance":
        if len(args) < 2:
            return "<on/off>"

        maintenance = args[1].lower() == "on"
        return await system_maintenance(maintenance)
    if additional_context == "restart":
        return await system_reload()
    if additional_context == "status":
        return await system_status()

    return "Subcommand not found"


@CrystalBot.register_command("!report")
async def report_user(args: List[str], token: "Player", _):
    if args:
        if len(args) < 2:
            return "I need reason!"
        if len(args) < 3:
            return "Maybe you will add some addition info?"
    else:
        return "Who should be reported?"

    target, reason, additionalInfo = (
        args[0].lower(),
        args[1],
        " ".join(args[2:]),
    )
    if target == CrystalBot.bot_name.lower():
        return "What have I done to offend you?"

    target_id = await userHelper.get_start_user(target)
    if not target_id:
        return "Who is this?"

    if reason.lower() == "other" and not additionalInfo:
        return "Maybe you will add some addition info?"

    chat_log = token.get_formatted_chatlog

    await Context.mysql.execute(
        """
INSERT INTO reports (id, from_uid, to_uid, reason, chatlog, time, assigned)
VALUES (NULL, :id, :tid, :reason, :chatlog, UNIX_TIMESTAMP(), 0)""",
        {
            "id": token.id,
            "tid": target_id["id"],
            "reason": f"{reason} - ingame {additionalInfo}",
            "chatlog": chat_log,
        },
    )

    msg = (
        f"You've reported {target} for {reason}({additionalInfo}). "
        "A Community Manager will check your report as soon as possible. "
        "Every !report message you may see in chat wasn't sent to anyone, "
        "so nobody in chat, but admins, know about your report. "
        "Thank you for reporting!"
    )
    return msg


@CrystalBot.register_command("!switchserver")
@CrystalBot.check_perms(need_perms=Privileges.ADMIN_MANAGE_SERVERS)
async def switch_server(args: List[str], *_):
    if not args or len(args) < 2:
        return "Enter in format: <username> <server_address>"

    target = args[0]
    new_server = args[1].strip()

    if not (to_token := Context.players.get_token(name=target.lower())):
        return "This dude currently not connected to bancho"

    to_token.enqueue(PacketBuilder.SwitchServer(new_server))

    return f"{to_token.name} has been connected to {new_server}"


@CrystalBot.register_command("!rtx")
@CrystalBot.check_perms(need_perms=Privileges.ADMIN_MANAGE_USERS)
async def rtx(args: List[str], *_):
    if not args or len(args) < 2:
        return "Enter in format: <username> <message>"

    target = args[0]
    message = " ".join(args[1:]).strip()
    if not (to_token := Context.players.get_token(name=target.lower())):
        return "Player is not online"

    to_token.enqueue(PacketBuilder.RTX(message))
    return "Pee-poo"


@CrystalBot.register_command("!kill")
@CrystalBot.check_perms(need_perms=Privileges.ADMIN_MANAGE_USERS)
async def kill(args: List[str], token: "Player", _):
    if not args:
        return "Enter in format: <username>"

    target = args[0]
    to_token = Context.players.get_token(name=target.lower())
    if to_token.privileges > token.privileges:
        return "You can't touch this dude"

    if not to_token:
        return "Player is not online"

    to_token.enqueue(
        PacketBuilder.BanchoPrivileges(BanchoRanks(BanchoRanks.SUPPORTER + BanchoRanks.PLAYER)),
    )
    to_token.enqueue(
        PacketBuilder.BanchoPrivileges(BanchoRanks(BanchoRanks.BAT + BanchoRanks.PLAYER)),
    )
    to_token.enqueue(PacketBuilder.KillPing())

    return "User should be happy now! Bye-bye"


@CrystalBot.register_command("!map")
@CrystalBot.check_perms(need_perms=Privileges.ADMIN_MANAGE_BEATMAPS)
async def map_rank(args: List[str], token: "Player", _):
    """
    SUPER UGLY CODE PORT FROM PEP.PY CMYUI !!!!! PREPARE YOUR EYES FOR BLOWN UP
    I warned!
    """
    if args:
        if not args[0] in ["rank", "love", "unrank"]:
            return "-_-"
        if len(args) < 2 or args[1] not in ["set", "map"]:
            return "set or map?"
        if len(args) < 3 or not args[2].isdigit():
            return "Maybe you can present me ID of map(bid)"
    else:
        return "rank/unrank/love ?"

    rank_type = args[0]
    map_type = args[1]
    map_id = args[2]

    # Figure out what to do
    if rank_type == "rank":
        rank_typed_str = "ranke"
        rank_type_id = 2
        freeze_status = 1
    elif rank_type == "love":
        rank_typed_str = "love"
        rank_type_id = 5
        freeze_status = 1
    elif rank_type == "unrank":
        rank_typed_str = "unranke"
        rank_type_id = 0
        freeze_status = 0
    else:
        rank_typed_str = "unranke"
        rank_type_id = 0
        freeze_status = 0

    # Grab beatmap_data from db
    beatmap_data = await Context.mysql.fetch_one(
        "SELECT * FROM beatmaps WHERE beatmap_id = :bid LIMIT 1",
        {"bid": map_id},
    )
    if not beatmap_data:
        return "Are you sure that you present bid(not set id)?"

    if map_type == "set":
        await Context.mysql.execute(
            "UPDATE beatmaps SET ranked = :rti, ranked_status_freezed = :freeze WHERE beatmapset_id = :sid LIMIT 100",
            {
                "rti": rank_type_id,
                "freeze": freeze_status,
                "sid": beatmap_data["beatmapset_id"],
            },
        )
        if freeze_status:
            await Context.mysql.execute(
                """
UPDATE scores s JOIN
(
    SELECT userid, MAX(score) maxscore FROM scores
    JOIN beatmaps ON scores.beatmap_md5 = beatmaps.beatmap_md5
    WHERE beatmaps.beatmap_md5 = (
        SELECT beatmap_md5 FROM beatmaps
        WHERE beatmapset_id = :sid LIMIT 1
    )
    GROUP BY userid
) s2 ON s.score = s2.maxscore AND s.userid = s2.userid SET completed = 3""",
                {"sid": beatmap_data["beatmapset_id"]},
            )
    elif map_type == "map":
        await Context.mysql.execute(
            "UPDATE beatmaps SET ranked = :rti, ranked_status_freezed = :freeze WHERE beatmap_id = :bid LIMIT 1",
            {"rti": rank_type_id, "freeze": freeze_status, "bid": map_id},
        )
        if freeze_status:
            await Context.mysql.execute(
                """
UPDATE scores s JOIN (
    SELECT userid, MAX(score) maxscore FROM scores
    JOIN beatmaps ON scores.beatmap_md5 = beatmaps.beatmap_md5
    WHERE beatmaps.beatmap_md5 = (
        SELECT beatmap_md5 FROM beatmaps
        WHERE beatmap_id = :bid LIMIT 1
    ) GROUP BY userid
) s2 ON s.score = s2.maxscore AND s.userid = s2.userid SET completed = 3""",
                {"bid": beatmap_data["beatmap_id"]},
            )
    else:
        return (
            "Please specify whether it is a set/map. eg: '!map unrank/rank/love set/map 123456'"
        )

    await userHelper.log_rap(
        token.id,
        f"has {rank_type}d beatmap ({map_type}): {beatmap_data['song_name']} ({map_id}).",
    )
    if map_type == "set":
        msg = (
            f"{token.name} has {rank_type}d beatmap set: [https://osu.ppy.sh/s/{beatmap_data['beatmapset_id']}"
            f" {beatmap_data['song_name']}]"
        )
    else:
        msg = f"{token.name} has loved beatmap: [https://osu.ppy.sh/s/{map_id} {beatmap_data['song_name']}]"

    await Context.mysql.execute(
        """
        UPDATE scores s
        JOIN (
            SELECT userid, MAX(score) maxscore
            FROM scores
            JOIN beatmaps ON scores.beatmap_md5 = beatmaps.beatmap_md5
            WHERE beatmaps.beatmap_md5 = (
                SELECT beatmap_md5 FROM beatmaps WHERE beatmap_id = :bid LIMIT 1
            ) GROUP BY userid
        ) s2 ON s.score = s2.maxscore AND s.userid = s2.userid SET completed = 2""",
        {"bid": beatmap_data["beatmap_id"]},
    )

    if Config.config["crystalbot_api"]:
        params = {
            "token": Config.config["crystalbot_token"],
            "poster": token.name,
            "type": rank_typed_str,
        }
        if map_type == "set":
            params["sid"] = beatmap_data["beatmapset_id"]
        else:
            params["bid"] = beatmap_data["beatmap_id"]

        async with aiohttp.ClientSession() as sess:
            async with sess.get(
                f'{Config.config["crystalbot_api"]}api/v1/submitMap',
                params=params,
            ):
                pass  # just send it and nothing more ;d

    await CrystalBot.ez_message(to="#nowranked", message=msg)
    return msg
