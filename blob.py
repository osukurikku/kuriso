"""
This file contains context features :sip:
"""

import os
from typing import Dict

import databases
import geoip2.database

import aioredis
import time
import git
import prometheus_client

from objects.TokenStorage import TokenStorage

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Multiplayer import Match
    from objects.Channel import Channel


class Context:
    """Singleton конфигурация"""

    players: TokenStorage = TokenStorage()
    channels: Dict[str, "Channel"] = {}
    matches: Dict[int, "Match"] = {}  # TODO: Union with matches
    matches_id: int = 1  # default value when bancho is up!

    motd: str = ""
    motd_html: str = ""

    mysql: databases.Database = None
    redis: aioredis.client.Redis = None
    redis_sub: aioredis.client.PubSub = None

    bancho_settings: dict = {}

    version: str = ""
    commit_id: str = ""

    start_time: int = int(time.time())
    is_shutdown: bool = False

    geoip_db: geoip2.database.Reader = None

    stats: Dict[str, prometheus_client.Gauge] = {
        "online_users": prometheus_client.Gauge(
            "kuriso_online_users",
            "Counter of online users on kuriso",
        ),
        "multiplayer_matches": prometheus_client.Gauge(
            "kuriso_multiplayer_matches",
            "Count of multiplayer matches on kuriso",
        ),
        "osu_versions": prometheus_client.Gauge(
            "kuriso_most_osu_versions",
            "Most popular osu versions right now!",
            ("osu_version",),
        ),
        "devclient_usage": prometheus_client.Gauge(
            "kuriso_devclient_usage",
            "Usage of devserver right now",
            ("host",),
        ),
    }

    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super().__new__(cls)
        return cls.instance

    @classmethod
    def load_version(cls):
        # просто моя хотелка
        repo = git.Repo(search_parent_directories=True)
        cls.commit_id = repo.head.object.hexsha[0:7]

        with open("version", encoding="utf-8") as file_ver:
            cls.version = file_ver.read()

    @classmethod
    async def load_bancho_settings(cls):
        # load primary settings
        for setting in await cls.mysql.fetch_all("select * from bancho_settings"):
            cls.bancho_settings[setting["name"]] = (
                setting["value_string"]
                if bool(setting["value_string"])
                else setting["value_int"]
            )

        menu_icon = await cls.mysql.fetch_one(
            "select file_id, url from main_menu_icons where is_current = 1 limit 1",
        )
        if menu_icon:
            image_url = f"https://i.kurikku.pw/{menu_icon['file_id']}.png"
            cls.bancho_settings["menu_icon"] = f"{image_url}|{menu_icon['url']}"

    @classmethod
    def load_motd(cls):
        with open("kuriso.MOTD", encoding="utf-8") as motd_file:
            cls.motd = motd_file.read()

        with open("kuriso.HTTP", encoding="utf-8") as motd_file:
            cls.motd_html = motd_file.read()

    @classmethod
    def try_to_load_geoip2(cls) -> bool:
        PATH = "./ext/GeoLite2-City.mmdb"
        if not os.path.exists(PATH):
            return False

        cls.geoip_db = geoip2.database.Reader(PATH)
        return True
