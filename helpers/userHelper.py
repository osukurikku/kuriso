import asyncio
import time

import bcrypt
from typing import Union, Tuple, List, TYPE_CHECKING

if TYPE_CHECKING:
    from objects import Player, TourneyPlayer
from objects.constants import Privileges
from blob import Context
from lib import logger

from functools import lru_cache


@lru_cache(maxsize=64)
def check_pw(password: bytes, db_password: bytes) -> bool:
    """Just wondering how it will work"""
    return bcrypt.checkpw(password, db_password)


async def check_login(login: str, password: str, ip: str):
    safe_login = login.lower().strip().replace(" ", "_")
    user = await Context.mysql.fetch(
        "SELECT id, password_md5, salt, password_version FROM users WHERE username_safe = %s", [safe_login]
    )

    if not user:
        return False

    user_bancho_session_exist = (await Context.redis.exists(f"peppy:sessions:{user['id']}")) or \
                                (await Context.redis.sismember(f"peppy:sessions:{user['id']}", ip)) if ip else False
    if user_bancho_session_exist:
        await Context.redis.srem(f"peppy:sessions:{user['id']}", ip)

    if len(password) != 32:
        return False

    password = password.encode("utf-8")
    db_password = user['password_md5'].encode("utf-8")

    return check_pw(password, db_password)


async def get_start_user(login: str) -> Union[None, dict]:
    safe_login = login.lower().strip().replace(" ", "_")

    user = await Context.mysql.fetch(
        'select id, username, silence_end, privileges, donor_expire from users where username_safe = %s',
        [safe_login]
    )
    if not user:
        return None

    return user


async def get_start_user_id(user_id: int) -> Union[None, dict]:
    user = await Context.mysql.fetch(
        'select id, username, silence_end, privileges, donor_expire from users where id = %s',
        [user_id]
    )
    if not user:
        return None

    return user


async def get_username(user_id: int) -> Union[str, None]:
    r = await Context.mysql.fetch(
        'select username from users where id = %s',
        [user_id]
    )
    return r.get('username', None)


async def user_have_hardware(user_id: int) -> bool:
    hardware = await Context.mysql.fetch(
        "SELECT id FROM hw_user WHERE userid = %s AND activated = 1 LIMIT 1",
        [user_id]
    )
    return bool(hardware)


async def get_country(user_id: int) -> str:
    r = await Context.mysql.fetch(
        "SELECT country FROM users_stats WHERE id = %s LIMIT 1",
        [user_id]
    )
    return r["country"]


async def append_notes(user_id: int, notes: Union[Tuple[str], List[str]], add_date: bool = True):
    to_apply = ""
    if add_date:
        to_apply += f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] "

    to_apply += '\n'.join(notes)
    await Context.mysql.execute(
        "update users set notes = concat(coalesce(notes, ''), %s) where id = %s limit 1",
        [notes, user_id]
    )
    return True


async def remove_from_leaderboard(user_id: int) -> bool:
    # Remove the user from global and country leaderboards, for every mode
    country = (await get_country(user_id)).lower()
    tasks = []
    for mode in ["std", "taiko", "ctb", "mania"]:
        # я не буду это трогать, тк подозреваю, что оно там всё хранится в стрингАх
        tasks.append(Context.redis.zrem("ripple:leaderboard:{}".format(mode), str(user_id)))
        # этож надо было сравнивать длину, когда у нативтайпа всегда будет False, если объект пустой *кхм-кхм*
        if country and country != "xx":
            tasks.append(Context.redis.zrem("ripple:leaderboard:{}:{}".format(mode, country), str(user_id)))

    await asyncio.gather(*tasks)  # запускаем это в асинхрон, потому что меня не ебёт
    return True


async def ban(user_id: int) -> bool:
    ban_time = int(time.time())
    await Context.mysql.execute(
        "UPDATE users SET privileges = privileges & %s, ban_datetime = %s WHERE id = %s LIMIT 1",
        [~(Privileges.USER_NORMAL | Privileges.USER_PUBLIC), ban_time, user_id]
    )

    # Notify our ban handler about the ban
    await Context.redis.publish("peppy:ban", str(user_id))
    # Remove the user from global and country leaderboards
    await remove_from_leaderboard(user_id)
    return True


async def unban(user_id: int) -> bool:
    await Context.mysql.execute(
        "UPDATE users SET privileges = privileges | %s, ban_datetime = 0 WHERE id = %s LIMIT 1",
        [(Privileges.USER_NORMAL | Privileges.USER_PUBLIC), user_id]
    )
    await Context.redis.publish("peppy:ban", str(user_id))
    return True


async def restrict(user_id: int) -> bool:
    user = await get_start_user_id(user_id)
    if not ((user["privileges"] & Privileges.USER_NORMAL) and not (user["privileges"] & Privileges.USER_PUBLIC)):
        ban_datetime = int(time.time())
        await Context.mysql.execute(
            'update users set privileges = privileges & %s, ban_datetime = %s where id = %s LIMIT 1',
            [~Privileges.USER_PUBLIC, ban_datetime, user_id]
        )

        await Context.redis.publish("peppy:ban", str(user_id))  # а вот тут передаётся integer, вот какого чёрта
        await remove_from_leaderboard(user_id)

    return True


async def activate_user(user_id: int, user_name: str, hashes: Union[Tuple[str], List[str]]) -> bool:
    if len(hashes) < 5 or not all((x for x in hashes)):
        logger.elog(f"[Verification/{user_id}] have wrong hash set! Probably generated by randomizer")
        return False

    match: dict
    if hashes[2] == "b4ec3c4334a0249dae95c284ec5983df" or \
            hashes[4] == "ffae06fb022871fe9beb58b005c5e21d":
        # user logins from wine(old bancho checks)
        match = await Context.mysql.fetch(
            "select userid from hw_user where unique_id = %(unique_id)s and userid != %(userid)s and activated = 1 limit 1",
            {
                'unique_id': hashes[3],
                'userid': user_id
            }
        )
    else:
        # its 100%(prob 80%) windows
        match = await Context.mysql.fetch(
            'select userid from hw_user '
            'where mac = %(mac)s and unique_id = %(unique_id)s '
            'and disk_id = %(disk_id)s '
            'and userid != %(userid)s '
            'and activated = 1 LIMIT 1',
            {
                "mac": hashes[2],
                "unique_id": hashes[3],
                "disk_id": hashes[4],
                "userid": user_id
            }
        )

    await Context.mysql.execute(
        'update users set privileges = privileges & %s where id = %s limit 1',
        [~Privileges.USER_PENDING_VERIFICATION, user_id]
    )
    if match:
        source_user_id = match['userid']
        source_user_name = (await get_username(source_user_id))

        # баним его
        await ban(source_user_id)
        # уведомляем стафф, что это читерюга и как-бы ну нафиг.
        await append_notes(user_id, [
            f"{source_user_name}\'s multiaccount ({hashes[2:5]}),found HWID match while verifying account ({user_id})"
        ])
        await append_notes(source_user_id, [f"Has created multiaccount {user_name} ({user_id})"])
        logger.klog(f"[{source_user_name}] Has created multiaccount {user_name} ({user_id})")
        return False

    await Context.mysql.execute(
        "UPDATE users SET privileges = privileges | %s WHERE id = %s LIMIT 1",
        [(Privileges.USER_PUBLIC | Privileges.USER_NORMAL), user_id]
    )
    return True


async def add_friend(user_id: int, friend_id: int) -> bool:
    await Context.mysql.execute(
        'INSERT INTO users_relationships (user1, user2) VALUES (%s, %s)',
        [user_id, friend_id]
    )
    return True


async def remove_friend(user_id: int, friend_id: int) -> bool:
    await Context.mysql.execute(
        'DELETE FROM users_relationships WHERE user1 = %s AND user2 = %s',
        [user_id, friend_id]
    )
    return True


async def setUserLastOsuVer(user_id: int, osu_ver: str) -> bool:
    await Context.mysql.execute(
        "UPDATE users SET osuver = %s WHERE id = %s LIMIT 1",
        [osu_ver, user_id]
    )
    return True


async def saveBanchoSession(user_id: int, ip: str) -> bool:
    await Context.redis.sadd(f"peppy:sessions:{user_id}", ip)
    return True


async def deleteBanchoSession(user_id: int, ip: str) -> bool:
    await Context.redis.srem(f"peppy:sessions:{user_id}", ip)
    return True


async def log_rap(user_id: int, message: str, through: str = "Crystal"):
    await Context.mysql.execute(
        "INSERT INTO rap_logs (id, userid, text, datetime, through) VALUES (NULL, %s, %s, %s, %s)",
        [user_id, message, int(time.time()), through]
    )
    return True


async def getSilenceEnd(user_id: int) -> int:
    return (await Context.mysql.fetch(
        "SELECT silence_end FROM users WHERE id = %s LIMIT 1",
        [user_id]
    ))["silence_end"]


async def silence(user_id: int, seconds: int, silence_reason: str, author: int = 999) -> bool:
    # db qurey
    silenceEndTime = int(time.time()) + seconds
    await Context.mysql.execute(
        "UPDATE users SET silence_end = %s, silence_reason = %s WHERE id = %s LIMIT 1",
        [silenceEndTime, silence_reason, user_id]
    )

    # Log
    targetUsername = await get_username(user_id)
    if not targetUsername:
        return False

    if seconds > 0:
        await log_rap(author, "has silenced {} for {} seconds for the following reason: \"{}\""
                      .format(targetUsername, seconds, silence_reason))
    else:
        await log_rap(author, "has removed {}'s silence".format(targetUsername))

    return True


class InvalidUsernameError(Exception):
    pass


class UsernameAlreadyInUseError(Exception):
    pass


async def changeUsername(user_id: int = 0, old_username: str = "", new_username: str = "") -> bool:
    """
        Change `userID`'s username to `newUsername` in database

        :param user_id: user id. Required only if `oldUsername` is not passed.
        :param old_username: username. Required only if `userID` is not passed.
        :param new_username: new username. Can't contain spaces and underscores at the same time.
        :raise: invalidUsernameError(), usernameAlreadyInUseError()
        :return: bool
    """
    # Make sure new username doesn't have mixed spaces and underscores
    if " " in new_username and "_" in new_username:
        raise InvalidUsernameError()

    # Get safe username
    newUsernameSafe = new_username.lower().strip().replace(" ", "_")

    # Make sure this username is not already in use
    if await get_start_user(newUsernameSafe):
        raise UsernameAlreadyInUseError()

    # Get userID or oldUsername
    if user_id == 0:
        data = await get_start_user(old_username)
        if data:
            user_id = data['id']
    else:
        old_username = await get_username(user_id)

    # Change username
    await Context.mysql.execute(
        "UPDATE users SET username = %s, username_safe = %s WHERE id = %s LIMIT 1",
        [new_username, newUsernameSafe, user_id]
    )
    await Context.mysql.execute(
        "UPDATE users_stats SET username = %s WHERE id = %s LIMIT 1",
        [new_username, user_id]
    )

    # Empty redis username cache
    await Context.redis.delete(f"ripple:userid_cache:{old_username.lower().strip().replace(' ', '_')}")
    await Context.redis.delete(f"ripple:change_username_pending:{user_id}")
    return True


async def handle_username_change(user_id: int, new_username: str,
                                 target_token: Union['Player', 'TourneyPlayer'] = None) -> bool:
    try:
        await changeUsername(user_id, new_username=new_username)
        if target_token:
            await target_token.kick(f"Your username has been changed to {new_username}. Please log in again.")
            await append_notes(user_id, [f"Username change: '{target_token.name}' -> '{new_username}'"])
    except UsernameAlreadyInUseError:
        await log_rap(999, f"Username change: {new_username} is already in use!", through="Kuriso")
        if target_token:
            target_token.kick(
                "There was a critical error while trying to change your username. Please contact a developer.",
                "username_change_fail")
    except InvalidUsernameError:
        await log_rap(999, f"Username change: {new_username} is not a valid username!", through="Kuriso")
        if target_token:
            target_token.kick(
                "There was a critical error while trying to change your username. Please contact a developer.",
                "username_change_fail")
    return True
