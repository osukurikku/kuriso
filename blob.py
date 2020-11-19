"""
This file contains context features :sip:
"""

from lib import AsyncSQLPoolWrapper
import asyncio_redis
import git

from objects.TokenStorage import TokenStorage


class Context:
    """Singleton конфигурация"""
    players: TokenStorage = TokenStorage()
    channels: dict = {}
    matches = []  # TODO: Union with matches

    mysql: AsyncSQLPoolWrapper = None
    redis: asyncio_redis.RedisProtocol = None

    bancho_settings: dict = {}

    version: str = ""
    commit_id: str = ""

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Context, cls).__new__(cls)
        return cls.instance

    @classmethod
    def load_version(cls):
        # просто моя хотелка
        repo = git.Repo(search_parent_directories=True)
        cls.commit_id = repo.head.object.hexsha[0:7]
        ver = open("version", encoding="utf-8", mode="r").read()
        cls.version = ver

    @classmethod
    async def load_bancho_settings(cls):
        # load primary settings
        async for setting in cls.mysql.iterall("select * from bancho_settings"):
            cls.bancho_settings[setting['name']] = setting['value_string'] if bool(setting['value_string']) \
                else setting['value_int']

        menu_icon = await cls.mysql.fetch("select file_id, url from main_menu_icons where is_current = 1 limit 1")
        if menu_icon:
            image_url = f"https://i.kurikku.pw/{menu_icon['file_id']}.png"
            cls.bancho_settings['menu_icon'] = f"{image_url}|{menu_icon['url']}"
