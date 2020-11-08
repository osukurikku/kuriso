import queue
from typing import Optional, Union, List
import uuid
import aiohttp

from blob import BlobContext
from config import Config
from lib import logger
from objects import Countries, Privileges
from objects.BanchoRanks import BanchoRanks
from objects.GameModes import GameModes
from objects.IdleStatuses import Action
from objects.KurikkuPrivileges import KurikkuPrivileges
from objects.Modificatiors import Modifications
from objects.TypedDicts import TypedStats, TypedStatus


# I wan't use construction in python like <class>.__dict__.update
# but i forgot if class has __slots__ __dict__ is unavailable, sadly ;-;
class StatsMode:
    __slots__ = ("game_mode", "total_score", "ranked_score", "pp",
                 "accuracy", "total_plays", "playtime", "max_combo", "leaderboard_rank")

    def __init__(self):
        self.total_score: int = 0
        self.ranked_score: int = 0
        self.pp: int = 0
        self.accuracy: float = 0.00
        self.total_plays: int = 0
        self.playtime: int = 0
        self.leaderboard_rank: int = 0

    def update(self, **kwargs: TypedStats):
        self.total_score = kwargs.get('total_score', 0)
        self.ranked_score = kwargs.get('ranked_score', 0)
        self.pp = kwargs.get('pp', 0)
        self.accuracy = kwargs.get('accuracy', 0)
        self.total_plays = kwargs.get('total_plays', 0)
        self.playtime = kwargs.get('playtime', 0)
        self.leaderboard_rank = kwargs.get('leaderboard_rank', 0)


class Status:
    __slots__ = (
        'action', 'action_text', 'map_md5',
        'mods', 'mode', 'map_id'
    )

    def __init__(self):
        self.action: Action = Action.Idle
        self.action_text: str = ''
        self.map_md5: str = ''
        self.mode: GameModes = GameModes.STD
        self.mods: Modifications = Modifications.NOMOD
        self.map_id: int = 0

    def update(self, **kwargs: TypedStatus):
        self.action = kwargs.get('action', Action.Idle)
        self.action_text = kwargs.get('action_text', '')
        self.map_md5 = kwargs.get('map_md5', '')
        self.mode = kwargs.get('mode', GameModes.STD)
        self.mods = kwargs.get('mods', Modifications.NOMOD)
        self.map_id = kwargs.get('map_id', 0)


class Player:

    def __init__(self, user_id: Union[int], user_name: Union[str],
                 privileges: Union[int], utc_offset: Optional[int] = 0,
                 pm_private: bool = False, silence_end: int = 0):
        self.token: str = self.generate_token()
        self.id: int = user_id
        self.name: str = user_name
        self.privileges = privileges
        self.selected_game_mode = GameModes.STD

        self.stats: dict = {mode: StatsMode() for mode in GameModes}  # setup dictionary with stats
        self.pr_status: Status = Status()

        self.country = (0, 'XX')
        self.location = (0.0, 0.0)
        self.timezone = 24 + utc_offset
        self.timezone_offset = utc_offset

        self.pm_private = pm_private  # Как я понял, это типо только друзья могут писать
        self.friends: Union[List[int]] = []
        self.away_msg: Optional[str] = None
        self.silence_end = silence_end

        self.presence_filter: int = 0  # TODO: Enum
        self.bot_np: Optional[dict] = None  # TODO: Beatmap

        self.channels: Union[List[dict]] = []  # TODO: Channels
        self.match: Optional[dict] = None  # TODO: Match
        self.friends: Union[List[int]] = []  # bot by default xd

        self.queue: queue.Queue = queue.Queue()  # main thing

    @property
    def is_queue_empty(self) -> bool:
        return self.queue.empty()

    @property
    def bancho_privs(self) -> bool:
        privs = BanchoRanks(0)
        if self.privileges & KurikkuPrivileges.Normal:
            privs |= (BanchoRanks.PLAYER | BanchoRanks.SUPPORTER)
        if self.privileges & KurikkuPrivileges.Bat:
            privs |= BanchoRanks.BAT
        if (self.privileges & KurikkuPrivileges.ChatMod) or (self.privileges & KurikkuPrivileges.ReplayModerator):
            privs |= BanchoRanks.MOD
        if self.privileges & KurikkuPrivileges.CM:
            privs |= BanchoRanks.ADMIN
        if self.privileges & KurikkuPrivileges.Owner:
            privs |= BanchoRanks.PEPPY

        return privs

    @property
    def current_stats(self) -> StatsMode:
        return self.stats[self.selected_game_mode]

    @classmethod
    def generate_token(cls) -> str:
        return str(uuid.uuid4())

    async def parse_friends(self) -> bool:
        async for friend in BlobContext.mysql.iterall(
                'select user2 from users_relationships where user1 = %s',
                [self.id]
        ):
            self.friends.append(friend['user2'])

        return True

    async def parse_country(self, ip: str) -> bool:
        if (self.privileges & Privileges.USER_DONOR) > 0:
            # we need to remember donor have locked location
            donor_location: str = (await BlobContext.mysql.fetch(
                'select country from users_stats where id = %s',
                [self.id]
            ))['country'].upper()
            self.country = (Countries.get_country_id(donor_location), donor_location)
        else:
            data = None
            async with aiohttp.ClientSession() as sess:
                async with sess.get(Config.config['geoloc_ip'] + ip) as resp:
                    try:
                        data = await resp.json()
                    finally:
                        pass

            if not data:
                logger.elog(f"[Player/{self.name}] Can't parse geoloc")
                return False

            self.country = (Countries.get_country_id(data['country']), data['country'])
            loc = data['loc'].split(",")
            self.location = (float(loc[0]), float(loc[1]))
            return True

    async def update_stats(self, selected_mode: GameModes = None) -> bool:
        for mode in GameModes if not selected_mode else [selected_mode]:
            res = await BlobContext.mysql.fetch(
                'select total_score_{0} as total_score, ranked_score_{0} as ranked_score, '
                'pp_{0} as pp, playcount_{0} as total_plays, avg_accuracy_{0} as accuracy, playtime_{0} as playtime '
                'from users_stats where id = %s'.format(GameModes.resolve_to_str(mode)),
                [self.id]
            )

            if not res:
                logger.elog(f"[Player/{self.name}] Can't parse stats for {GameModes.resolve_to_str(mode)}")
                return False

            print(f"ripple:leaderboard:{GameModes.resolve_to_str(mode)}")
            position = await BlobContext.redis.zrevrank(
                f"ripple:leaderboard:{GameModes.resolve_to_str(mode)}",
                str(self.id)
            )
            print(position, type(position))
            res['leaderboard_rank'] = int(position) + 1 if position else 0
            print(res['leaderboard_rank'])

            self.stats[mode].update(**res)

    def enqueue(self, b: bytes) -> None:
        self.queue.put_nowait(b)

    def dequeue(self) -> Optional[bytes]:
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            pass
