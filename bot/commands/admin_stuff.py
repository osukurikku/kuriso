import asyncio
from typing import List, TYPE_CHECKING, Any

import aiohttp

from blob import Context
from bot.bot import CrystalBot
from config import Config
from helpers import userHelper
from lib import logger
from objects.constants import Privileges
from objects.constants.KurikkuPrivileges import KurikkuPrivileges
from packets.Builder.index import PacketBuilder

if TYPE_CHECKING:
    from objects.Player import Player


@CrystalBot.register_command("!alert")
@CrystalBot.check_perms(need_perms=KurikkuPrivileges.CM)
async def alert(args: List[Any], _):
    if not args:
        return 'What do you wanna to say?'

    notify_packet = await PacketBuilder.Notification(' '.join(args))
    for user in Context.players.get_all_tokens(ignore_tournament_clients=True):
        user.enqueue(notify_packet)

    return 'Await your msg!'


@CrystalBot.register_command("!useralert", aliases=["!alertuser"])
@CrystalBot.check_perms(need_perms=KurikkuPrivileges.CM)
async def user_alert(args: List[Any], _):
    if args:
        if len(args) < 2:
            return 'What do you wanna to say?'
    else:
        return 'Who do you want to write to?'

    name = args[0].lower()
    text = ' '.join(args[1:])

    to_token = Context.players.get_token(name=name)
    if not to_token:
        return 'User not found'

    notify_packet = await PacketBuilder.Notification(text)
    to_token.enqueue(notify_packet)
    return 'Message was sent'


@CrystalBot.register_command("!kickall")
@CrystalBot.check_perms(need_perms=KurikkuPrivileges.CM)
async def kick_all(*_):
    tasks = []
    for user in Context.players.get_all_tokens():
        if user.is_admin:
            continue

        tasks.append(user.kick())

    await asyncio.gather(*tasks)
    return 'All kicked!'


@CrystalBot.register_command("!kick")
@CrystalBot.check_perms(need_perms=KurikkuPrivileges.CM)
async def kick(args: List[Any], _):
    if not args:
        return 'Who do you want to kick?'

    username = args[0]
    if len(args) > 1:
        username = '_'.join(args).lower()

    to_token = Context.players.get_token(name=username)
    if not to_token:
        return 'User not found'

    if to_token.is_admin:
        return 'User is admin, you can\'t kick him'

    await to_token.kick()
    return 'User kicked successfully'


@CrystalBot.register_command("!silence")
@CrystalBot.check_perms(need_perms=KurikkuPrivileges.ChatMod)
async def silence(args: List[Any], player: 'Player'):
    if args:
        if len(args) < 2:
            return 'You need put amount'
        if len(args) < 3 or args[2].lower() not in ['s', 'm', 'h', 'd']:
            return 'You need to set unit s/m/h/d'
        if len(args) < 4:
            return 'You need to put reason'
    else:
        return 'I need nickname who you want to silence'

    target = args[0]
    amount = args[1]
    unit = args[2]
    reason = ' '.join(args[3:]).strip()
    if not amount.isdigit():
        return "The amount must be a number."

    # Calculate silence seconds
    if unit == 's':
        silenceTime = int(amount)
    elif unit == 'm':
        silenceTime = int(amount) * 60
    elif unit == 'h':
        silenceTime = int(amount) * 3600
    elif unit == 'd':
        silenceTime = int(amount) * 86400
    else:
        return "Invalid time unit (s/m/h/d)."

    # Max silence time is 7 days
    if silenceTime > 604800:
        return "Invalid silence time. Max silence time is 7 days."

    to_token = Context.players.get_token(name=target.lower())
    if to_token:
        if to_token.id == player.id or \
                to_token.privileges >= player.privileges:
            return 'You can\'t silence that dude'

        await to_token.silence(silenceTime, reason, player.id)
        logger.klog(f"[Player/{to_token.name}] has been silenced for following reason: {reason}")
        return 'User silenced'

    offline_user = await userHelper.get_start_user(target.lower())
    if offline_user['privileges'] > player.privileges:
        return 'You can\'t silence that dude'

    if not offline_user:
        return 'User not found!'

    res = await userHelper.silence(offline_user['id'], silenceTime, reason, player.id)
    if not res:
        return 'Not silenced!'

    logger.klog(f"[Player/{offline_user['username']}] has been silenced for following reason: {reason}")
    return 'User successfully silenced'


@CrystalBot.register_command("!removesilence")
@CrystalBot.check_perms(need_perms=KurikkuPrivileges.ChatMod)
async def remove_silence(args: List[Any], player: 'Player'):
    if not args:
        return 'I need nickname who you want to remove the silence'

    target = args[0]

    to_token = Context.players.get_token(name=target.lower())
    if to_token:
        logger.klog(f"[Player/{to_token.name}] silence reset")
        await to_token.silence(0, "", player.id)
        return 'User silenced'

    offline_user = await userHelper.get_start_user(target.lower())
    if not offline_user:
        return 'User not found!'

    res = await userHelper.silence(offline_user['id'], 0, "", player.id)
    if not res:
        return 'Not silenced!'

    logger.klog(f"[Player/{offline_user['username']}] silence reset")
    return 'User successfully silenced'


@CrystalBot.register_command("!ban")
@CrystalBot.check_perms(need_perms=Privileges.ADMIN_BAN_USERS)
async def ban(args: List[Any], player: 'Player'):
    if not args:
        return 'Which player should be banned?'

    offline_user = await userHelper.get_start_user(args[0].lower())
    if not offline_user:
        return 'Player not found'

    if offline_user['privileges'] > player.privileges:
        return 'You can\'t silence that dude'

    await userHelper.ban(offline_user['id'])

    # send packet to user if he's online
    to_token = Context.players.get_token(name=args[0].lower())
    if to_token:
        to_token.enqueue(await PacketBuilder.UserID(-1))

    if Config.config['crystalbot_api']:
        params = {
            'token': Config.config['crystalbot_token'],
            'banned': offline_user['username'],
            'type': 1,
            'author': player.name
        }
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f'{Config.config["crystalbot_api"]}api/v1/submitBanOrRestrict',
                                params=params):
                pass  # just send it and nothing more ;d

    await userHelper.log_rap(player.id, f'has banned {offline_user["username"]}')
    return 'Player has been banned'


@CrystalBot.register_command("!lock")
@CrystalBot.check_perms(need_perms=Privileges.ADMIN_BAN_USERS)
async def lock(args: List[Any], player: 'Player'):
    if not args:
        return 'Which player should be locked?'

    to_token = Context.players.get_token(name=args[0].lower())
    if not to_token:
        return 'Player not found'

    if to_token.privileges > player.privileges:
        return 'You can\'t touch this player'

    to_token.enqueue(await PacketBuilder.UserID(-3))  # ban client id
    return 'Player\'s client has been locked'


@CrystalBot.register_command("!unban")
@CrystalBot.check_perms(need_perms=Privileges.ADMIN_BAN_USERS)
async def unban(args: List[Any], player: 'Player'):
    if not args:
        return 'Which player should unbanned?'

    offline_user = await userHelper.get_start_user(args[0].lower())
    if not offline_user:
        return 'User not found!'

    await userHelper.unban(offline_user['id'])

    if Config.config['crystalbot_api']:
        params = {
            'token': Config.config['crystalbot_token'],
            'banned': offline_user['username'],
            'type': 1,
            'author': player.name
        }
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f'{Config.config["crystalbot_api"]}api/v1/submitBanOrRestrict',
                                params=params):
                pass  # just send it and nothing more ;d

    await userHelper.log_rap(player.id, f'has unbanned {offline_user["username"]}')
    return f'Welcome back {offline_user["username"]}'


@CrystalBot.register_command("!restrict")
@CrystalBot.check_perms(need_perms=Privileges.ADMIN_BAN_USERS)
async def restrict(args: List[Any], player: 'Player'):
    if not args:
        return 'Which player should be restricted?'

    offline_user = await userHelper.get_start_user(args[0].lower())
    if not offline_user:
        return 'Player not found'

    if offline_user['privileges'] > player.privileges:
        return 'You can\'t silence that dude'

    await userHelper.restrict(offline_user['id'])

    # send packet to user if he's online
    to_token = Context.players.get_token(name=args[0].lower())
    if to_token:
        to_token.privileges &= ~Privileges.USER_PUBLIC
        to_token.enqueue(await PacketBuilder.UserRestricted())
        await CrystalBot.ez_message(
            args[0].lower(),
            "Your account is currently in restricted mode. Please visit kurikku's website for more information."
        )

    if Config.config['crystalbot_api']:
        params = {
            'token': Config.config['crystalbot_token'],
            'banned': offline_user['username'],
            'type': 0,
            'author': player.name
        }
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f'{Config.config["crystalbot_api"]}api/v1/submitBanOrRestrict',
                                params=params):
                pass  # just send it and nothing more ;d

    await userHelper.log_rap(player.id, f'has restricted {offline_user["username"]}')
    return 'Player has been restricted'


@CrystalBot.register_command("!unrestrict")
@CrystalBot.check_perms(need_perms=Privileges.ADMIN_BAN_USERS)
async def unrestrict(args: List[Any], player: 'Player'):
    if not args:
        return 'Which player should unrestrict?'

    offline_user = await userHelper.get_start_user(args[0].lower())
    if not offline_user:
        return 'User not found!'

    await userHelper.unban(offline_user['id'])

    to_token = Context.players.get_token(uid=offline_user['id'])
    if to_token:
        await to_token.logout()  # чтоб права себе обновил дурачок, а то вот ещё, никаких пакетов не получил, а ещё хочет играть ;d

    if Config.config['crystalbot_api']:
        params = {
            'token': Config.config['crystalbot_token'],
            'banned': offline_user['username'],
            'type': 2,
            'author': player.name
        }
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f'{Config.config["crystalbot_api"]}api/v1/submitBanOrRestrict',
                                params=params):
                pass  # just send it and nothing more ;d

    await userHelper.log_rap(player.id, f'has unrestricted {offline_user["username"]}')
    return f'Welcome back {offline_user["username"]}'
