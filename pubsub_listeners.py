"""
Hard-coded
"""
import asyncio
import traceback
from sentry_sdk import capture_exception

import aioredis

from blob import Context
from config import Config
from helpers import userHelper, new_utils
from lib import logger
from objects.constants.BanchoRanks import BanchoRanks
from objects.constants.IdleStatuses import Action
from packets.Builder.index import PacketBuilder


async def disconnect_handler(ch: aioredis.Channel) -> bool:
    try:
        data = await ch.get_json()
        if not data.get("userID", 0):
            raise ValueError("userID must be integer")

        token = Context.players.get_token(uid=data.get("userID"))
        if token:
            await token.kick(reason=data.get("reason", ""))
    except Exception as e:
        capture_exception(e)
        traceback.print_exc()
        return False

    return True


async def notification(ch: aioredis.Channel) -> bool:
    try:
        data = await ch.get_json()
        if not data.get("userID", 0):
            raise ValueError("userID must be integer")

        token = Context.players.get_token(uid=data.get("userID"))
        if token:
            token.enqueue(await PacketBuilder.Notification(data.get("message", "")))
    except Exception as e:
        capture_exception(e)
        traceback.print_exc()
        return False

    return True


async def change_username(ch: aioredis.Channel) -> bool:
    try:
        data = await ch.get_json()
        if not data.get("userID", 0):
            raise ValueError("userID must be integer")

        token = Context.players.get_token(uid=data.get("userID"))
        if token:
            if token.pr_status.action not in (Action.Playing, Action.Multiplayer_play):
                await userHelper.handle_username_change(
                    data.get("userID"), data.get("newUsername"), token
                )
            else:
                await Context.redis.set(
                    f"ripple:change_username_pending:{data.get('userID')}",
                    data.get("newUsername"),
                )
        else:
            await Context.redis.set(
                f"ripple:change_username_pending:{data.get('userID')}",
                data.get("newUsername"),
            )
    except Exception as e:
        capture_exception(e)
        traceback.print_exc()
        return False

    return True


async def reload_settings(ch: aioredis.Channel) -> bool:
    return await ch.get() == b"reload" and await new_utils.reload_settings()


async def update_cached_stats(ch: aioredis.Channel) -> bool:
    data = await ch.get()
    if not data.isdigit():
        return False

    token = Context.players.get_token(uid=int(data))
    if token:
        await token.update_stats()

    return True


async def silence(ch: aioredis.Channel) -> bool:
    data = await ch.get()
    if not data.isdigit():
        return False

    userID = int(data)
    token = Context.players.get_token(uid=userID)
    if token:
        await token.silence()

    return True


async def ban(ch: aioredis.Channel) -> bool:
    data = await ch.get()
    if not data.isdigit():
        return False

    userID = int(data)
    token = Context.players.get_token(uid=userID)
    if token:
        await userHelper.ban(token.id)
        await token.kick("You are banned. Join our discord for additional information.")

    return True


async def killHQUser(ch: aioredis.Channel) -> bool:
    data = await ch.get()
    if not data.isdigit():
        return False

    userID = int(data)
    token = Context.players.get_token(uid=userID)
    if token:
        token.enqueue(await PacketBuilder.Notification("Bye-bye! See ya!"))
        token.enqueue(
            await PacketBuilder.BanchoPrivileges(
                BanchoRanks(BanchoRanks.SUPPORTER + BanchoRanks.PLAYER)
            )
        )
        token.enqueue(
            await PacketBuilder.BanchoPrivileges(
                BanchoRanks(BanchoRanks.BAT + BanchoRanks.PLAYER)
            )
        )
        token.enqueue(await PacketBuilder.KillPing())

    return True


MAPPED_FUNCTIONS = {
    b"peppy:disconnect": disconnect_handler,
    b"peppy:change_username": change_username,
    b"peppy:reload_settings": reload_settings,
    b"peppy:update_cached_stats": update_cached_stats,
    b"peppy:silence": silence,
    b"peppy:ban": ban,
    b"peppy:notification": notification,
    b"kotrik:hqosu": killHQUser,
}


async def sub_reader(ch: aioredis.Channel):
    while await ch.wait_message():
        if ch.name in MAPPED_FUNCTIONS:
            logger.klog(f"[Redis/Pubsub] Received event in {ch.name}")
            await MAPPED_FUNCTIONS[ch.name](ch)


async def init():
    redis_values = dict(db=Config.config["redis"]["db"])
    if Config.config["redis"]["password"]:
        redis_values["password"] = Config.config["redis"]["password"]

    subscriber = await aioredis.create_redis(
        f"redis://{Config.config['redis']['host']}", **redis_values
    )

    subscribed_channels = await subscriber.subscribe(
        *[k for (k, _) in MAPPED_FUNCTIONS.items()]
    )

    Context.redis_sub = subscriber

    loop = asyncio.get_event_loop()
    for ch in subscribed_channels:
        loop.create_task(sub_reader(ch))
    return True
