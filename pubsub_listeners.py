"""
Hard-coded
"""
import asyncio
import traceback

import async_timeout
from sentry_sdk import capture_exception

import aioredis

from blob import Context
from config import Config
from helpers import userHelper, new_utils
from lib import logger
from objects.constants.BanchoRanks import BanchoRanks
from objects.constants.IdleStatuses import Action
from packets.Builder.index import PacketBuilder
import json


async def disconnect_handler(_, message: dict) -> bool:
    try:
        print(message)
        data = json.loads(message["data"])
        if not data.get("userID", 0):
            raise ValueError("userID must be integer")

        if token := Context.players.get_token(uid=data.get("userID")):
            await token.kick(reason=data.get("reason", ""))
    except Exception as e:
        capture_exception(e)
        traceback.print_exc()
        return False

    return True


async def notification(_, message: dict) -> bool:
    try:
        data = json.loads(message["data"])
        if not data.get("userID", 0):
            raise ValueError("userID must be integer")

        if token := Context.players.get_token(uid=data.get("userID")):
            token.enqueue(PacketBuilder.Notification(data.get("message", "")))
    except Exception as e:
        capture_exception(e)
        traceback.print_exc()
        return False

    return True


async def change_username(redis: aioredis.client.Redis, message: dict) -> bool:
    try:
        data = json.loads(message["data"])
        if not data.get("userID", 0):
            raise ValueError("userID must be integer")

        if token := Context.players.get_token(uid=data.get("userID")):
            if token.pr_status.action not in (Action.Playing, Action.Multiplayer_play):
                await userHelper.handle_username_change(
                    data.get("userID"),
                    data.get("newUsername"),
                    token,
                )
            else:
                await redis.set(
                    f"ripple:change_username_pending:{data.get('userID')}",
                    data.get("newUsername"),
                )
        else:
            await redis.set(
                f"ripple:change_username_pending:{data.get('userID')}",
                data.get("newUsername"),
            )
    except Exception as e:
        capture_exception(e)
        traceback.print_exc()
        return False

    return True


async def reload_settings(_, message: dict) -> bool:
    return message["data"] == b"reload" and await new_utils.reload_settings()


async def update_cached_stats(_, message: dict) -> bool:
    data = message["data"]
    if not data.isdigit():
        return False

    if token := Context.players.get_token(uid=data.get("userID")):
        await token.update_stats()

    return True


async def silence(_, message: dict) -> bool:
    data = message["data"]
    if not data.isdigit():
        return False

    user_id = int(data)
    if token := Context.players.get_token(uid=user_id):
        await token.silence()

    return True


async def ban(_, message: dict) -> bool:
    data = message["data"]
    if not data.isdigit():
        return False

    user_id = int(data)
    if token := Context.players.get_token(uid=user_id):
        await userHelper.ban(token.id)
        await token.kick("You are banned. Join our discord for additional information.")

    return True


async def killHQUser(_, message: dict) -> bool:
    data = message["data"]
    if not data.isdigit():
        return False

    user_id = int(data)
    if token := Context.players.get_token(uid=user_id):
        token.enqueue(PacketBuilder.Notification("Bye-bye! See ya!"))
        token.enqueue(
            PacketBuilder.BanchoPrivileges(
                BanchoRanks(BanchoRanks.SUPPORTER + BanchoRanks.PLAYER),
            ),
        )
        token.enqueue(
            PacketBuilder.BanchoPrivileges(BanchoRanks(BanchoRanks.BAT + BanchoRanks.PLAYER)),
        )
        token.enqueue(PacketBuilder.KillPing())

    return True


MAPPED_FUNCTIONS = {
    "peppy:disconnect": disconnect_handler,
    "peppy:change_username": change_username,
    "peppy:reload_settings": reload_settings,
    "peppy:update_cached_stats": update_cached_stats,
    "peppy:silence": silence,
    "peppy:ban": ban,
    "peppy:notification": notification,
    "kotrik:hqosu": killHQUser,
}


async def sub_reader(subscriber: aioredis.client.Redis, ch: aioredis.client.PubSub):
    while True:
        try:
            async with async_timeout.timeout(1):
                message = await ch.get_message(ignore_subscribe_messages=True)
                if message is not None:
                    channel = message["channel"]
                    if channel in MAPPED_FUNCTIONS:
                        logger.klog(f"<Redis/Pubsub> Received event in {channel}")
                        await MAPPED_FUNCTIONS[channel](subscriber, message)
                await asyncio.sleep(0.01)
        except asyncio.TimeoutError:
            pass
        except RuntimeError:
            pass


async def init():
    redis_values = dict(db=Config.config["redis"]["db"])
    if Config.config["redis"]["password"]:
        redis_values["password"] = Config.config["redis"]["password"]

    pubsub = Context.redis.pubsub()

    await pubsub.subscribe(*[k for (k, _) in MAPPED_FUNCTIONS.items()])

    Context.redis_sub = pubsub

    future = asyncio.create_task(sub_reader(Context.redis, pubsub))
    asyncio.ensure_future(future)
    return True
