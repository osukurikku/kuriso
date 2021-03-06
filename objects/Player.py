import time
from typing import Optional, Union, List, Dict, Tuple
import uuid
import aiohttp

from blob import Context
from config import Config
from helpers import userHelper
from lib import logger
from objects.Multiplayer import Match
from objects.constants import Privileges, Countries
from objects.constants.BanchoRanks import BanchoRanks
from objects.constants.GameModes import GameModes
from objects.constants.IdleStatuses import Action
from objects.constants.KurikkuPrivileges import KurikkuPrivileges
from objects.constants.Modificators import Mods
from objects.constants.PresenceFilter import PresenceFilter

from packets.Builder.index import PacketBuilder
from objects.Channel import Channel

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from objects.TypedDicts import TypedStats
    from objects.BanchoObjects import Message


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

    def update(self, **kwargs: 'TypedStats'):
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
        self.mods: Mods = Mods.NoMod
        self.map_id: int = 0

    def update(self, **kwargs):
        self.action = Action(kwargs.get('action', 0))
        self.action_text = kwargs.get('action_text', '')
        self.map_md5 = kwargs.get('map_md5', '')
        self.mode = GameModes(kwargs.get('mode', 0))
        self.mods = Mods(kwargs.get('mods', 0))
        self.map_id = kwargs.get('map_id', 0)


class Player:

    def __init__(self, user_id: Union[int], user_name: Union[str],
                 privileges: Union[int], utc_offset: Optional[int] = 0,
                 pm_private: bool = False, silence_end: int = 0, is_tourneymode: bool = False,
                 is_bot: bool = False, ip: str = ''):
        self.token: str = self.generate_token()
        self.id: int = user_id
        self.name: str = user_name
        self.ip: str = ip
        self.privileges: int = privileges
        self.selected_game_mode: GameModes = GameModes.STD

        self.stats: Dict[GameModes, StatsMode] = {mode: StatsMode() for mode in GameModes}  # setup dictionary with stats
        self.pr_status: Status = Status()

        self.spectators: List[Player] = []
        self.spectating: Optional[Player] = None

        self.country: Tuple[int, str] = (0, 'XX')
        self.location: Tuple[float, float] = (0.0, 0.0)
        self.timezone: int = 24 + utc_offset
        self.timezone_offset: int = utc_offset

        self.pm_private: bool = pm_private  # Как я понял, это типо только друзья могут писать
        self.friends: Union[List[int]] = []
        self.away_msg: Optional[str] = None
        self.silence_end: int = silence_end

        self.presence_filter: PresenceFilter = PresenceFilter(1)
        self.bot_np: Optional[dict] = None  # TODO: Beatmap

        self._match: Optional[Match] = None
        self.friends: Union[List[int]] = []  # bot by default xd

        self.queue: bytearray = bytearray()  # main thing
        self.login_time: int = int(time.time())
        self.last_packet_unix: int = int(time.time())

        self.is_tourneymode: bool = is_tourneymode
        self.id_tourney: int = -1
        self.is_in_lobby: bool = False

        self.is_bot: bool = is_bot
        self.tillerino: List[Union[int, Mods]] = [0, Mods(0)]  # 1 - map id, 2 - current_mods <- legacy code
        self.user_chat_log: List['Message'] = []

    @property
    def match(self):
        return self._match

    @property
    def get_formatted_chatlog(self):
        return "\n".join(
            f"{time.strftime('%H:%M', time.localtime(message.when))} - {self.name}@{message.to}: {message.body[:50]}"
            for message in self.user_chat_log
        )

    @property
    def silenced(self) -> bool:
        return self.silence_end > 0

    @property
    def safe_name(self) -> str:
        return self.name.lower().strip().replace(" ", "_")

    @property
    def is_restricted(self) -> bool:
        return (self.privileges & Privileges.USER_NORMAL) and not (self.privileges & Privileges.USER_PUBLIC)

    @property
    def bancho_privs(self) -> BanchoRanks:
        privs = BanchoRanks(0)
        if (self.privileges & KurikkuPrivileges.Normal.value) == KurikkuPrivileges.Normal.value:
            privs |= (BanchoRanks.PLAYER | BanchoRanks.SUPPORTER)
        if (self.privileges & KurikkuPrivileges.Bat.value) == KurikkuPrivileges.Bat.value:
            privs |= BanchoRanks.BAT
        if (self.privileges & KurikkuPrivileges.ChatMod.value) == KurikkuPrivileges.ChatMod.value or \
                (self.privileges & KurikkuPrivileges.ReplayModerator.value) == KurikkuPrivileges.ReplayModerator.value:
            privs |= BanchoRanks.MOD
        if (self.privileges & KurikkuPrivileges.CM.value) == KurikkuPrivileges.CM.value:
            privs |= BanchoRanks.ADMIN
        if (self.privileges & KurikkuPrivileges.Owner.value) == KurikkuPrivileges.Owner.value:
            privs |= BanchoRanks.PEPPY

        return privs

    @property
    def is_admin(self) -> bool:
        if (self.privileges & KurikkuPrivileges.Developer) == KurikkuPrivileges.Developer or \
                (self.privileges & KurikkuPrivileges.ChatMod) == KurikkuPrivileges.ChatMod or \
                (self.privileges & KurikkuPrivileges.CM) == KurikkuPrivileges.CM:
            return True

        return False

    @property
    def current_stats(self) -> StatsMode:
        return self.stats[self.selected_game_mode]

    @classmethod
    def generate_token(cls) -> str:
        return str(uuid.uuid4())

    async def parse_friends(self) -> bool:
        async for friend in Context.mysql.iterall(
                'select user2 from users_relationships where user1 = %s',
                [self.id]
        ):
            self.friends.append(friend['user2'])

        return True

    async def parse_country(self, ip: str) -> bool:
        if self.privileges & Privileges.USER_DONOR:
            # we need to remember donor have locked location
            donor_location: str = (await Context.mysql.fetch(
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
            res = await Context.mysql.fetch(
                'select total_score_{0} as total_score, ranked_score_{0} as ranked_score, '
                'pp_{0} as pp, playcount_{0} as total_plays, avg_accuracy_{0} as accuracy, playtime_{0} as playtime '
                'from users_stats where id = %s'.format(GameModes.resolve_to_str(mode)),
                [self.id]
            )

            if not res:
                logger.elog(f"[Player/{self.name}] Can't parse stats for {GameModes.resolve_to_str(mode)}")
                return False

            position = await Context.redis.zrevrank(
                f"ripple:leaderboard:{GameModes.resolve_to_str(mode)}",
                str(self.id)
            )
            res['leaderboard_rank'] = int(position) + 1 if position else 0

            self.stats[mode].update(**res)

    async def logout(self) -> None:
        if not self.is_tourneymode:
            if self.ip:
                await userHelper.deleteBanchoSession(self.id, self.ip)
        # logic
        # leave multiplayer
        if self.match:
            await self.match.leave_player(self)
        # leave specatating
        if self.spectating:
            await self.spectating.remove_spectator(self)

        # leave channels
        for (_, chan) in Context.channels.items():
            if self.id in chan.users:
                await chan.leave_channel(self)

        if not self.is_tourneymode:
            for p in Context.players.get_all_tokens():
                p.enqueue(await PacketBuilder.Logout(self.id))

        Context.players.delete_token(self)
        return

    async def kick(self, message: str = "You have been kicked from the server. Please login again.",
                   reason: str = "kick") -> bool:
        if self.is_bot:
            return False

        logger.wlog(f"[Player/{self.name}] has been disconnected. {reason}")
        if message:
            self.enqueue(await PacketBuilder.Notification(message))
        self.enqueue(await PacketBuilder.UserID(-1))  # login failed

        await self.logout()
        return True

    # legacy code
    async def silence(self, seconds: int = None, reason: str = "", author: int = 999) -> bool:
        if seconds is None:
            # Get silence expire from db if needed
            seconds = max(0, await userHelper.getSilenceEnd(self.id) - int(time.time()))
        else:
            # Silence in db and token
            await userHelper.silence(self.id, seconds, reason, author)

        # Silence token
        self.silence_end = int(time.time()) + seconds

        # Send silence packet to user
        self.enqueue(await PacketBuilder.SilenceEnd(seconds))

        # Send silenced packet to everyone else
        user_silenced = await PacketBuilder.UserSilenced(self.id)
        for user in Context.players.get_all_tokens():
            user.enqueue(user_silenced)

        return True

    async def send_message(self, message: 'Message') -> bool:
        message.body = f'{message.body[:2045]}...' if message.body[2048:] else message.body

        chan: str = message.to
        if chan.startswith("#"):
            # this is channel object
            if chan.startswith("#multi"):
                if self.is_tourneymode:
                    if self.id_tourney > 0:
                        chan = f"#multi_{self.id_tourney}"
                    else:
                        return False
                else:
                    chan = f"#multi_{self.match.id}"
            elif chan.startswith("#spec"):
                if self.spectating:
                    chan = f"#spec_{self.spectating.id}"
                else:
                    chan = f"#spec_{self.id}"

            channel: 'Channel' = Context.channels.get(chan, None)
            if not channel:
                logger.klog(f"[{self.name}] Tried to send message in unknown channel. Ignoring it...")
                return False

            self.user_chat_log.append(message)
            logger.klog(
                f"{self.name}({self.id}) -> {channel.server_name}: {bytes(message.body, 'latin_1').decode()}"
            )
            await channel.send_message(self.id, message)
            return True

        # DM
        receiver = Context.players.get_token(name=message.to.lower())
        if not receiver:
            logger.klog(f"[{self.name}] Tried to offline user. Ignoring it...")
            return False

        if receiver.pm_private and self.id not in receiver.friends:
            self.enqueue(await PacketBuilder.PMBlocked(message.to))
            logger.klog(f"[{self.name}] Tried message {message.to} which has private PM.")
            return False

        if self.pm_private and receiver.id not in self.friends:
            self.pm_private = False
            logger.klog(f"[{self.name}] which has private pm sended message to non-friend user. PM unlocked")

        if receiver.silenced:
            self.enqueue(await PacketBuilder.TargetSilenced(message.to))
            logger.klog(f'[{self.name}] Tried message {message.to}, but has been silenced.')
            return False

        self.user_chat_log.append(message)
        logger.klog(
            f"#DM {self.name}({self.id}) -> {message.to}({receiver.id}): {bytes(message.body, 'latin_1').decode()}"
        )

        receiver.enqueue(
            await PacketBuilder.BuildMessage(self.id, message)
        )
        return True

    async def add_spectator(self, new_spec: 'Player') -> bool:
        spec_chan_name = f"#spec_{self.id}"
        if not Context.channels.get(spec_chan_name):
            # in this case, we need to create channel for our spectator in temp mode
            spec = Channel(
                server_name=spec_chan_name,
                description=f"Spectator channel for {self.name}",
                public_read=True,
                public_write=True,
                temp_channel=True
            )

            Context.channels[spec_chan_name] = spec
            await spec.join_channel(self)

        c: 'Channel' = Context.channels.get(spec_chan_name)
        if not await c.join_channel(new_spec):
            logger.elog(f"{self.name} failed to join in {spec_chan_name} spectator channel!")
            return False

        fellow_packet = await PacketBuilder.FellowSpectatorJoined(new_spec.id)
        for spectator in self.spectators:
            spectator.enqueue(fellow_packet)
            new_spec.enqueue(await PacketBuilder.FellowSpectatorJoined(spectator.id))

        self.spectators.append(new_spec)
        new_spec.spectating = self

        self.enqueue(await PacketBuilder.SpectatorJoined(new_spec.id))
        logger.slog(f"{new_spec.name} started to spectating {self.name}!")
        return True

    async def add_hidden_spectator(self, new_spec: 'Player') -> bool:
        self.spectators.append(new_spec)
        new_spec.spectating = self

        self.enqueue(await PacketBuilder.SpectatorJoined(new_spec.id))
        logger.slog(f"{new_spec.name} started to spectating {self.name}!")
        return True

    async def remove_spectator(self, old_spec: 'Player') -> bool:
        spec_chan_name = f"#spec_{self.id}"
        self.spectators.remove(old_spec)  # attempt to remove old player from array
        old_spec.spectating = None

        spec_chan: Channel = Context.channels.get(spec_chan_name)
        await spec_chan.leave_channel(old_spec)  # remove our spectator from channel

        fellow_packet = await PacketBuilder.FellowSpectatorLeft(old_spec.id)
        if not self.spectators:
            await spec_chan.leave_channel(self)
        else:
            for spectator in self.spectators:
                spectator.enqueue(fellow_packet)

        self.enqueue(await PacketBuilder.SpectatorLeft(old_spec.id))
        logger.slog(f"{old_spec.name} has stopped hidden spectating for {self.name}")
        return True

    async def remove_hidden_spectator(self, old_spec: 'Player') -> bool:
        self.spectators.remove(old_spec)  # attempt to remove old player from array
        old_spec.spectating = None

        self.enqueue(await PacketBuilder.SpectatorLeft(old_spec.id))
        logger.slog(f"{old_spec.name} has stopped hidden spectating for {self.name}")
        return True
    
    async def say_bancho_restarting(self, delay: int=20) -> bool:
        self.enqueue(
            await PacketBuilder.BanchoRestarting(delay*1000)
        )
        return True

    def enqueue(self, b: bytes) -> None:
        self.queue += b

    def dequeue(self) -> Optional[bytes]:
        if self.queue:
            data = bytes(self.queue)
            self.queue.clear()
            return data

        return b''
