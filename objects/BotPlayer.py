import random
from typing import Optional, TYPE_CHECKING

from blob import Context
from lib import logger
from objects.Player import Status, Player
from objects.constants import Countries
from objects.constants.GameModes import GameModes
from objects.constants.IdleStatuses import Action

if TYPE_CHECKING:
    from objects.BanchoObjects import Message
    from objects.Channel import Channel


class BotPlayer(Player):
    def __init__(
        self,
        user_id: int,
        user_name: str,
        privileges: int,
        utc_offset: Optional[int] = 0,
        pm_private: bool = False,
        silence_end: int = 0,
        is_tourneymode: bool = False,
        is_bot: bool = True,
        ip: str = "",
    ):
        super().__init__(
            user_id,
            user_name,
            privileges,
            utc_offset,
            pm_private,
            silence_end,
            is_tourneymode,
            is_bot,
            ip,
        )

        bot_pr = Status()
        bot_pr.update(
            action=Action.Testing.value,
            action_text=random.choice(
                [
                    "\n-- Sotarks is gone! --",
                    "\n-- ck was here --",
                    "\n-- Welcome to Kurikku --",
                    "\n-- osu!godland is deprecated --",
                    "\n-- rarenai #1 in 2019 --",
                    "\n-- Reedkatt #1 in 2020 --",
                    "\n-- Maybe u wanna play HDDTHR? --",
                    "\n-- flipzky should do tourneys!!!!!! ;d --",
                    "\n-- use chimu.moe instead of bloodcat.com --",
                    "\n-- i wanna 100 players online ;d --",
                ]
            ),
        )

        self.pr_status = bot_pr

    @property
    def is_queue_empty(self) -> bool:
        return True

    @property
    def silenced(self) -> bool:
        return False

    async def parse_country(self, *_) -> bool:
        donor_location: str = (
            await Context.mysql.fetch_one(
                "select country from users_stats where id = :id", {"id": self.id}
            )
        )["country"].upper()
        self.country = (
            Countries.get_country_id(donor_location),
            donor_location,
        )

        self.location = (0, 0)
        return True

    async def update_stats(self, selected_mode: GameModes = None) -> bool:
        for mode in GameModes if not selected_mode else [selected_mode]:
            # pylint: disable=consider-using-f-string
            res = await Context.mysql.fetch_one(
                "select total_score_{0} as total_score, ranked_score_{0} as ranked_score, "
                "pp_{0} as pp, playcount_{0} as total_plays, avg_accuracy_{0} as accuracy, playtime_{0} as playtime "
                "from users_stats where id = :id".format(GameModes.resolve_to_str(mode)),
                {"id": self.id},
            )

            if not res:
                logger.elog(
                    f"[Player/{self.name}] Can't parse stats for {GameModes.resolve_to_str(mode)}"
                )
                return False

            self.stats[mode].update(**{**res, **{"leaderboard_rank": 0}})
        return True

    async def logout(self) -> None:
        # leave channels
        for (_, chan) in Context.channels.items():
            if self.id in chan.users:
                await chan.leave_channel(self)

        if not self.is_tourneymode:
            for p in Context.players.get_all_tokens():
                await p.on_another_user_logout(self)

        Context.players.delete_token(self)
        return

    async def send_message(self, message: "Message") -> bool:
        message.body = f"{message.body[:2045]}..." if message.body[2048:] else message.body

        chan: str = message.to
        if chan.startswith("#"):
            channel: "Channel" = Context.channels.get(chan, None)
            if not channel:
                logger.klog(
                    f"<{self.name}/Bot> Tried to send message in unknown channel. Ignoring it..."
                )
                return False

            logger.klog(f"{self.name}({self.id})/Bot -> {channel.server_name}: {message.body}")
            await channel.send_message(self.id, message)
            return True

        # DM
        receiver = Context.players.get_token(name=message.to.lower().strip().replace(" ", "_"))
        if not receiver:
            logger.klog(f"<{self.name}> Tried to offline user. Ignoring it...")
            return False

        logger.klog(
            f"#DM {self.name}({self.id})/Bot -> {message.to}({receiver.id}): {message.body}"
        )

        await receiver.on_message(self.id, message)
        return True

    async def kick(self, *_) -> bool:
        return True

    async def silence(self, *_) -> bool:
        return True

    async def add_spectator(self, *_) -> bool:
        return True

    async def remove_spectator(self, *_) -> bool:
        return True

    async def remove_hidden_spectator(self, *_) -> bool:
        return True

    def enqueue(self, *_):
        return

    def dequeue(self, *_) -> bytes:
        return b""
