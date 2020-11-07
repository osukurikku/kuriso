from typing import Union

import bcrypt as bcrypt

from blob import BlobContext


async def check_login(login: str, password: str, ip: str):
    safe_login = login.lower().strip().replace(" ", "_")
    user = await BlobContext.mysql.fetch(
        "SELECT id, password_md5, salt, password_version FROM users WHERE username_safe = %s", [safe_login]
    )

    if not user:
        return False

    user_bancho_session_exist = (await BlobContext.redis.exists(f"peppy:sessions:{user['id']}")) or \
                                (await BlobContext.redis.sismember(f"peppy:sessions:{user['id']}", ip)) if ip else False
    if user_bancho_session_exist:
        return False

    if len(password) != 32:
        return False

    password = password.encode("utf-8")
    db_password = user['password_md5'].encode("utf-8")
    return bcrypt.checkpw(password, db_password)


async def get_start_user(login: str) -> Union[None, dict]:
    safe_login = login.lower().strip().replace(" ", "_")

    user = await BlobContext.mysql.fetch(
        'select id, username, silence_end, privileges, donor_expire from users where username_safe = %s',
        [safe_login]
    )
    if not user:
        return None

    return user
