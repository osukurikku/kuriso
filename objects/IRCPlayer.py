from typing import Optional, TYPE_CHECKING

from blob import Context
from helpers import userHelper
from lib import logger
from objects.Player import Player, Status
from objects.constants import Countries
from objects.constants.IdleStatuses import Action
from objects.BanchoObjects import Message

if TYPE_CHECKING:
    from objects.Channel import Channel
    from objects.Multiplayer import Match
    from irc import IRCClient


class IRCPlayer(Player):
    """
    Implementation of Player instance optimized for irc usage!
    """

    def __init__(
        self,
        user_id: int,
        user_name: str,
        privileges: int,
        utc_offset: Optional[int] = 0,
        pm_private: bool = False,
        silence_end: int = 0,
        is_tourneymode: bool = False,
        ip: str = "",
        irc: "IRCClient" = None,
    ):
        super().__init__(
            user_id,
            user_name,
            privileges,
            utc_offset,
            pm_private,
            silence_end,
            is_tourneymode,
            False,
            ip,
        )
        bot_pr = Status()
        bot_pr.update(
            action=Action.Idle.value,
            action_text="website user",
        )

        self.pr_status = bot_pr
        self.irc = irc
        self.token = self.generate_token()

    @property
    def match(self) -> "Match":
        return None if self.id_tourney < 0 else Context.matches.get(self.id_tourney, None)

    @property
    def is_queue_empty(self) -> bool:
        return True

    async def parse_country(self, *_) -> bool:
        donor_location: str = (
            await Context.mysql.fetch_one(
                "select country from users_stats where id = :id",
                {"id": self.id},
            )
        )["country"].upper()
        self.country = (
            Countries.get_country_id(donor_location),
            donor_location,
        )

        self.location = (0, 0)
        return True

    async def logout(self) -> None:
        if not self.is_tourneymode:
            await Context.redis.set(
                "ripple:online_users",
                len(Context.players.get_all_tokens(True)),
            )
            if self.ip:
                await userHelper.deleteBanchoSession(self.id, self.ip)

        # leave channels
        for (_, chan) in Context.channels.items():
            if self.id in chan.users:
                await chan.leave_channel(self)

        if not self.is_tourneymode:
            for p in Context.players.get_all_tokens():
                await p.on_another_user_logout(self)

        self.irc.writer.close()

        Context.players.delete_token(self)
        return

    async def kick(
        self,
        message: str = "You have been kicked from the server. Please login again.",
        reason: str = "kick",
    ) -> bool:
        logger.wlog(f"[Player/{self.name}] has been disconnected. {reason}")
        await self.logout()
        return True

    async def send_message(self, message: "Message") -> bool:
        message.body = f"{message.body[:2045]}..." if message.body[2048:] else message.body

        chan: str = message.to
        if chan.startswith("#"):
            # this is channel object
            channel: "Channel" = Context.channels.get(chan, None)
            if not channel:
                logger.klog(
                    f"<{self.name}/irc> Tried to send message in unknown channel. Ignoring it...",
                )
                return False

            self.user_chat_log.append(message)
            logger.klog(f"{self.name}/irc({self.id}) -> {channel.server_name}: {message.body}")
            await channel.send_message(self.id, message)
            return True

        # DM
        receiver = Context.players.get_token(name=message.to.lower().strip().replace(" ", "_"))
        if not receiver:
            logger.klog(f"<{self.name}/irc> Tried to offline user. Ignoring it...")
            return False

        if receiver.pm_private and self.id not in receiver.friends:
            self.irc.queue += f":{str(self.irc)} PRIVMSG Crystal Hey! {message.to} have private PM! Please don't distribute him right now!"
            logger.klog(f"<{self.name}/irc> Tried message {message.to} which has private PM.")
            return False

        if self.pm_private and receiver.id not in self.friends:
            self.pm_private = False
            logger.klog(
                f"<{self.name}/irc> which has private pm send message to non-friend user. PM unlocked",
            )

        if receiver.silenced:
            logger.klog(f"<{self.name}/irc> Tried message {message.to}, but has been silenced.")
            return False

        self.user_chat_log.append(message)
        logger.klog(
            f"#DM {self.name}/irc({self.id}) -> {message.to}({receiver.id}): {message.body}",
        )

        await receiver.on_message(self.id, message)
        return True

    async def on_another_user_logout(self, p: "Player") -> None:
        return self.irc.add_queue(f":{p.name} QUIT :Logged out")

    async def on_message(self, from_id: int, message: "Message", **kwargs) -> None:
        msg = message
        if "server_name" in kwargs:
            msg = Message(
                sender=msg.sender,
                to=kwargs["server_name"],
                body=msg.body,
                client_id=msg.client_id,
            )

        return self.irc.receive_message(msg)

    async def on_channel_another_user_join(self, p_name: str, **kwargs) -> None:
        return self.irc.add_queue(f":{p_name} JOIN :{kwargs['channel'].server_name}")

    async def on_channel_another_user_leave(self, p_name: str, **kwargs) -> None:
        return self.irc.add_queue(f":{p_name} PART :{kwargs['channel'].server_name}")

    async def on_channel_join(self, channel_name: str, server_name: str) -> None:
        return self.irc.add_queue(f":{self.name} JOIN :{server_name}")

    async def on_channel_leave(self, channel_name: str, server_name: str) -> None:
        return self.irc.add_queue(f":{self.name} PART :{server_name}")

    async def add_spectator(self, *_) -> bool:
        return True

    async def remove_spectator(self, *_) -> bool:
        return True

    async def remove_hidden_spectator(self, *_) -> bool:
        return True

    async def say_bancho_restarting(self, delay: int = 20) -> bool:
        return True

    def enqueue(self, *_):
        return

    def dequeue(self, *_) -> bytes:
        return b""
