"""
This file contains context features :sip:
"""
from typing import Dict

from lib import AsyncSQLPoolWrapper
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
    channels: Dict[str, 'Channel'] = {}
    matches: Dict[int, 'Match'] = {}  # TODO: Union with matches
    matches_id: int = 1  # default value when bancho is up!

    motd: str = ""
    motd_html: str = ""

    mysql: AsyncSQLPoolWrapper = None
    redis: aioredis.Redis = None
    redis_sub: aioredis.Redis = None

    bancho_settings: dict = {}

    version: str = ""
    commit_id: str = ""

    start_time: int = int(time.time())
    is_shutdown: bool = False

    stats: Dict[str, prometheus_client.Gauge] = {
        'online_users': prometheus_client.Gauge(
            "kuriso_online_users",
            "Counter of online users on kuriso"
        ),
        'multiplayer_matches': prometheus_client.Gauge(
            "kuriso_multiplayer_matches",
            "Count of multiplayer matches on kuriso"
        ),
        'osu_versions': prometheus_client.Counter(
            "kuriso_most_osu_versions",
            "Most popular osu versions right now!",
            ("osu_version",)
        ),
        'devclient_usage': prometheus_client.Counter(
            "kuriso_devclient_usage",
            "Usage of devserver right now",
            ("host",)
        )
    }

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

        '''
            МАЖОРНУЮ версию, когда сделаны обратно несовместимые изменения API.
            МИНОРНУЮ версию, когда вы добавляете новую функциональность, не нарушая обратной совместимости.
            ПАТЧ-версию, когда вы делаете обратно совместимые исправления.
        '''
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

    @classmethod
    def load_motd(cls):
        motd_file = open("kuriso.MOTD", "r", encoding="utf-8")
        cls.motd = motd_file.read()
        motd_file.close()

        motd_file = open("kuriso.HTTP", "r", encoding="utf-8")
        cls.motd_html = motd_file.read()
        motd_file.close()
