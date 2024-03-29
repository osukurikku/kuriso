import asyncio
import time

import bcrypt
from typing import Union, Tuple, List, TYPE_CHECKING, Optional, Mapping

from objects.constants import Privileges
from blob import Context
from lib import logger

from functools import lru_cache

# pylint: disable=wrong-import-position
if TYPE_CHECKING:
    from objects.Player import Player
    from objects.TourneyPlayer import TourneyPlayer


@lru_cache(maxsize=1024)
def check_pw(password: bytes, db_password: bytes) -> bool:
    """Just wondering how it will work"""
    return bcrypt.checkpw(password, db_password)


async def check_login(login: str, password: str, ip: str):
    safe_login = login.lower().strip().replace(" ", "_")
    user = await Context.mysql.fetch_one(
        "SELECT id, password_md5, salt, password_version FROM users WHERE username_safe = :username_safe",
        {"username_safe": safe_login},
    )

    if not user:
        return False

    user_bancho_session_exist = (
        (await Context.redis.exists(f"peppy:sessions:{user['id']}"))
        or (await Context.redis.sismember(f"peppy:sessions:{user['id']}", ip))
        if ip
        else False
    )
    if user_bancho_session_exist:
        await Context.redis.srem(f"peppy:sessions:{user['id']}", ip)

    if len(password) != 32:
        return False

    password = password.encode("utf-8")
    db_password = user["password_md5"].encode("utf-8")

    return check_pw(password, db_password)


async def get_start_user(login: str) -> Union[None, Optional[Mapping]]:
    safe_login = login.lower().strip().replace(" ", "_")

    user = await Context.mysql.fetch_one(
        "select id, username, silence_end, privileges, donor_expire from users where username_safe = :username_safe",
        {"username_safe": safe_login},
    )
    if not user:
        return None

    return user


async def get_start_user_id(user_id: int) -> Union[None, Optional[Mapping]]:
    user = await Context.mysql.fetch_one(
        "select id, username, silence_end, privileges, donor_expire from users where id = :id",
        {"id": user_id},
    )
    if not user:
        return None

    return user


async def get_username(user_id: int) -> Union[str, None]:
    r = await Context.mysql.fetch_one(
        "select username from users where id = :id",
        {"id": user_id},
    )
    if not r:
        return None
    return r[0]


async def user_have_hardware(user_id: int) -> bool:
    hardware = await Context.mysql.fetch_one(
        "SELECT id FROM hw_user WHERE userid = :id AND activated = 1 LIMIT 1",
        {"id": user_id},
    )
    return bool(hardware)


async def get_country(user_id: int) -> str:
    r = await Context.mysql.fetch_one(
        "SELECT country FROM users_stats WHERE id = :id LIMIT 1",
        {"id": user_id},
    )
    return r["country"]


async def set_country(user_id: int, country: str) -> bool:
    return await Context.mysql.execute(
        "UPDATE users_stats SET country = :country WHERE id = :id",
        {"country": country, "id": user_id},
    )


async def append_notes(
    user_id: int,
    notes: Union[Tuple[str], List[str]],
    add_date: bool = True,
    need_new_line: bool = True,
):
    to_apply = ""
    if add_date:
        to_apply += f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] "

    nl = "\n" if need_new_line else ""
    to_apply += nl.join(notes)
    await Context.mysql.execute(
        "update users set notes = concat(coalesce(notes, ''), :to_apply) where id = :id limit 1",
        {"to_apply": to_apply, "id": user_id},
    )
    return True


async def remove_from_leaderboard(user_id: int) -> bool:
    # Remove the user from global and country leaderboards, for every mode
    country = (await get_country(user_id)).lower()
    tasks = []
    for mode in ["std", "taiko", "ctb", "mania"]:
        # я не буду это трогать, тк подозреваю, что оно там всё хранится в стрингАх
        tasks.append(Context.redis.zrem(f"ripple:leaderboard:{mode}", str(user_id)))
        # этож надо было сравнивать длину, когда у нативтайпа всегда будет False, если объект пустой *кхм-кхм*
        if country and country != "xx":
            tasks.append(
                Context.redis.zrem(f"ripple:leaderboard:{mode}:{country}", str(user_id)),
            )

    await asyncio.gather(*tasks)  # запускаем это в асинхрон, потому что меня не ебёт
    return True


async def ban(user_id: int) -> bool:
    ban_time = int(time.time())
    await Context.mysql.execute(
        "UPDATE users SET privileges = privileges & :privileges, ban_datetime = :ban_time WHERE id = :id LIMIT 1",
        {
            "privileges": ~(Privileges.USER_NORMAL | Privileges.USER_PUBLIC),
            "ban_time": ban_time,
            "id": user_id,
        },
    )

    # Notify our ban handler about the ban
    await Context.redis.publish("peppy:ban", str(user_id))
    # Remove the user from global and country leaderboards
    await remove_from_leaderboard(user_id)
    return True


async def unban(user_id: int) -> bool:
    await Context.mysql.execute(
        "UPDATE users SET privileges = privileges | :privileges, ban_datetime = 0 WHERE id = :id LIMIT 1",
        {"privileges": (Privileges.USER_NORMAL | Privileges.USER_PUBLIC), "id": user_id},
    )
    await Context.redis.publish("peppy:ban", str(user_id))
    return True


async def restrict(user_id: int) -> bool:
    user = await get_start_user_id(user_id)
    if not (
        user["privileges"] & Privileges.USER_NORMAL
        and not user["privileges"] & Privileges.USER_PUBLIC
    ):
        ban_datetime = int(time.time())
        await Context.mysql.execute(
            "update users set privileges = privileges & :privileges , ban_datetime = :ban_time where id = :id LIMIT 1",
            {"privileges": ~Privileges.USER_PUBLIC, "ban_time": ban_datetime, "id": user_id},
        )

        await Context.redis.publish(
            "peppy:ban",
            str(user_id),
        )  # а вот тут передаётся integer, вот какого чёрта
        await remove_from_leaderboard(user_id)

    return True


async def activate_user(
    user_id: int,
    user_name: str,
    hashes: Union[Tuple[str], List[str]],
) -> bool:
    if len(hashes) < 5 or not all(x for x in hashes):
        logger.elog(
            f"[Verification/{user_id}] have wrong hash set! Probably generated by randomizer",
        )
        return False

    (
        _,
        _,
        adapters_md5,
        uninstall_md5,
        disk_sig_md5,
    ) = hashes

    match: Optional[Mapping]
    if (
        adapters_md5 == "b4ec3c4334a0249dae95c284ec5983df"
        or disk_sig_md5 == "ffae06fb022871fe9beb58b005c5e21d"
    ):
        # user logins from wine(old bancho checks)
        match = await Context.mysql.fetch_one(
            "select userid from hw_user where unique_id = :unique_id and userid != :userid and activated = 1 limit 1",
            {"unique_id": uninstall_md5, "userid": user_id},
        )
    else:
        # its 100%(prob 80%) windows
        match = await Context.mysql.fetch_one(
            "select userid from hw_user "
            "where mac = :mac and unique_id = :unique_id "
            "and disk_id = :disk_id "
            "and userid != :user_id "
            "and activated = 1 LIMIT 1",
            {
                "mac": adapters_md5,
                "unique_id": uninstall_md5,
                "disk_id": disk_sig_md5,
                "user_id": user_id,
            },
        )

    await Context.mysql.execute(
        "update users set privileges = privileges & :privileges where id = :id limit 1",
        {"privileges": ~Privileges.USER_PENDING_VERIFICATION, "id": user_id},
    )
    if match:
        source_user_id = match["userid"]
        source_user_name = await get_username(source_user_id)

        # баним его
        await ban(source_user_id)
        # уведомляем стафф, что это читерюга и как-бы ну нафиг.
        await append_notes(
            user_id,
            [
                f"{source_user_name}'s multiaccount ({hashes[2:5]}),found HWID match while verifying account ({user_id})",
            ],
        )

        await append_notes(
            source_user_id,
            [f"Has created multiaccount {user_name} ({user_id})"],
        )
        logger.klog(f"<{source_user_name}> Has created multiaccount {user_name} ({user_id})")
        return False

    await Context.mysql.execute(
        "UPDATE users SET privileges = privileges | :privileges WHERE id = :id LIMIT 1",
        {"privileges": (Privileges.USER_PUBLIC | Privileges.USER_NORMAL), "id": user_id},
    )

    await logHardware(user_id, hashes)
    await activateHardware(user_id, hashes)
    return True


async def add_friend(user_id: int, friend_id: int) -> bool:
    await Context.mysql.execute(
        "INSERT INTO users_relationships (user1, user2) VALUES (:user1, :user2)",
        {"user1": user_id, "user2": friend_id},
    )
    return True


async def remove_friend(user_id: int, friend_id: int) -> bool:
    await Context.mysql.execute(
        "DELETE FROM users_relationships WHERE user1 = :user1 AND user2 = :user2",
        {"user1": user_id, "user2": friend_id},
    )
    return True


async def setUserLastOsuVer(user_id: int, osu_ver: str) -> bool:
    await Context.mysql.execute(
        "UPDATE users SET osuver = :osu_ver WHERE id = :id LIMIT 1",
        {"osu_ver": osu_ver, "id": user_id},
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
        "INSERT INTO rap_logs (id, userid, text, datetime, through) VALUES (NULL, :id, :message, :time, :through)",
        {"id": user_id, "message": message, "time": int(time.time()), "through": through},
    )
    return True


async def getSilenceEnd(user_id: int) -> int:
    return (
        await Context.mysql.fetch_one(
            "SELECT silence_end FROM users WHERE id = :id LIMIT 1",
            {"id": user_id},
        )
    )["silence_end"]


async def silence(user_id: int, seconds: int, silence_reason: str, author: int = 999) -> bool:
    # db qurey
    silence_end_time = int(time.time()) + seconds
    await Context.mysql.execute(
        "UPDATE users SET silence_end = :end, silence_reason = :reason WHERE id = :id LIMIT 1",
        {"end": silence_end_time, "reason": silence_reason, "id": user_id},
    )

    # Log
    target_username = await get_username(user_id)
    if not target_username:
        return False

    if seconds > 0:
        await log_rap(
            author,
            f'has silenced {target_username} for {seconds} seconds for the following reason: "{silence_reason}"',
        )
    else:
        await log_rap(author, f"has removed {target_username}'s silence")

    return True


class InvalidUsernameError(Exception):
    pass


class UsernameAlreadyInUseError(Exception):
    pass


async def changeUsername(
    user_id: int = 0,
    old_username: str = "",
    new_username: str = "",
) -> bool:
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
            user_id = data["id"]
    else:
        old_username = await get_username(user_id)

    # Change username
    await Context.mysql.execute(
        "UPDATE users SET username = :username, username_safe = :username_safe WHERE id = :id LIMIT 1",
        {"username": new_username, "username_safe": newUsernameSafe, "id": user_id},
    )
    await Context.mysql.execute(
        "UPDATE users_stats SET username = :username WHERE id = :id LIMIT 1",
        {"username": new_username, "id": user_id},
    )

    # Empty redis username cache
    await Context.redis.delete(
        f"ripple:userid_cache:{old_username.lower().strip().replace(' ', '_')}",
    )
    await Context.redis.delete(f"ripple:change_username_pending:{user_id}")
    return True


async def handle_username_change(
    user_id: int,
    new_username: str,
    target_token: Union["Player", "TourneyPlayer"] = None,
) -> bool:
    try:
        await changeUsername(user_id, new_username=new_username)
        if target_token:
            await target_token.kick(
                f"Your username has been changed to {new_username}. Please log in again.",
            )
            await append_notes(
                user_id,
                [f"Username change: '{target_token.name}' -> '{new_username}'"],
            )
    except UsernameAlreadyInUseError:
        await log_rap(
            999,
            f"Username change: {new_username} is already in use!",
            through="Kuriso",
        )
        await Context.redis.delete(f"ripple:change_username_pending:{user_id}")
        if target_token:
            await target_token.kick(
                "There was a critical error while trying to change your username. Please contact a developer.",
                "username_change_fail",
            )
    except InvalidUsernameError:
        await log_rap(
            999,
            f"Username change: {new_username} is not a valid username!",
            through="Kuriso",
        )
        await Context.redis.delete(f"ripple:change_username_pending:{user_id}")
        if target_token:
            await target_token.kick(
                "There was a critical error while trying to change your username. Please contact a developer.",
                "username_change_fail",
            )
    return True


async def logHardware(user_id: int, hashes: List[str] = None) -> bool:
    if not hashes:
        return False

    await Context.mysql.execute(
        """
        INSERT INTO hw_user (userid, mac, unique_id, disk_id, occurencies) VALUES (:uid, :mac, :unique_id, :disk_id, 1)
        ON DUPLICATE KEY UPDATE occurencies = occurencies + 1""",
        {"uid": user_id, "mac": hashes[2], "unique_id": hashes[3], "disk_id": hashes[4]},
    )
    return True


async def activateHardware(user_id: int, hashes: List[str] = None) -> bool:
    if not hashes:
        return False

    await Context.mysql.execute(
        "UPDATE hw_user SET activated = 1 WHERE userid = :uid AND mac = :mac AND unique_id = :unique_id AND disk_id = :disk_id",
        {"uid": user_id, "mac": hashes[2], "unique_id": hashes[3], "disk_id": hashes[4]},
    )
    return True
