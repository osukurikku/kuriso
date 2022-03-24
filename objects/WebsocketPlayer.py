from typing import Optional, TYPE_CHECKING

import starlette.websockets
from starlette.websockets import WebSocketState

from blob import Context
from helpers import userHelper
from lib import logger
from lib.websocket_formatter import WebsocketEvent
from objects.Player import Player, Status
from objects.constants import Countries
from objects.constants.IdleStatuses import Action
from packets.Builder.index import PacketBuilder

if TYPE_CHECKING:
    from objects.Channel import Channel


class SafeWebSocket:
    def __init__(self, websocket: starlette.websockets.WebSocket):
        self.websocket = websocket

    async def send_json(self, data: dict, mode: str = "text"):
        if self.websocket.client_state in [
            WebSocketState.CONNECTING,
            WebSocketState.DISCONNECTED,
        ]:
            return False

        return await self.websocket.send_json(data, mode)


class WebsocketPlayer(Player):
    """
    Implementation of Player instance optimized for starlette websockets usage!
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
        socket: starlette.websockets.WebSocket = None,
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

        self.pr_status: Status = bot_pr
        self._websocket = socket
        self.is_socket_closing = False
        self.token = self.generate_token()

    @property
    def websocket(self):
        return SafeWebSocket(self._websocket)

    @property
    def is_queue_empty(self) -> bool:
        return True

    async def parse_country(self, *_) -> bool:
        donor_location: str = (
            await Context.mysql.fetch(
                "select country from users_stats where id = %s", [self.id]
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
                "ripple:online_users", len(Context.players.get_all_tokens(True))
            )
            if self.ip:
                await userHelper.deleteBanchoSession(self.id, self.ip)

        # leave channels
        for (_, chan) in Context.channels.items():
            if self.id in chan.users:
                await chan.leave_channel(self)

        if not self.is_tourneymode:
            for p in Context.players.get_all_tokens():
                if hasattr(p, "websocket"):
                    await p.websocket.send_json(WebsocketEvent.user_leaved(self.id))
                    continue
                p.enqueue(await PacketBuilder.Logout(self.id))

        self.is_socket_closing = True
        if self._websocket.client_state == WebSocketState.CONNECTED:
            await self._websocket.close()
        Context.players.delete_token(self)
        return

    async def kick(
        self,
        message: str = "You have been kicked from the server. Please login again.",
        reason: str = "kick",
    ) -> bool:
        logger.wlog(f"[Player/{self.name}] has been disconnected. {reason}")
        if message:

            self.enqueue(await PacketBuilder.Notification(message))
        await self.websocket.send_json(WebsocketEvent.error_disconnect("kick"))

        await self.logout()
        return True

    async def send_message(self, message: "Message") -> bool:
        message.body = f"{message.body[:2045]}..." if message.body[2048:] else message.body

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

            channel: "Channel" = Context.channels.get(chan, None)
            if not channel:
                logger.klog(
                    f"[{self.name}] Tried to send message in unknown channel. Ignoring it..."
                )
                return False

            self.user_chat_log.append(message)
            logger.klog(
                f"{self.name}({self.id}) -> {channel.server_name}: {bytes(message.body, 'latin_1').decode()}"
            )
            await channel.send_message(self.id, message)
            return True

        # DM
        receiver = Context.players.get_token(name=message.to.lower().strip().replace(" ", "_"))
        if not receiver:
            logger.klog(f"[{self.name}] Tried to offline user. Ignoring it...")
            return False

        if receiver.pm_private and self.id not in receiver.friends:
            await self.websocket.send_json(WebsocketEvent.failed_message("pm_private"))
            logger.klog(f"[{self.name}] Tried message {message.to} which has private PM.")
            return False

        if self.pm_private and receiver.id not in self.friends:
            self.pm_private = False
            logger.klog(
                f"[{self.name}] which has private pm sended message to non-friend user. PM unlocked"
            )

        if receiver.silenced:
            await self.websocket.send_json(
                WebsocketEvent.failed_message(f"silence:{message.to}")
            )
            logger.klog(f"[{self.name}] Tried message {message.to}, but has been silenced.")
            return False

        self.user_chat_log.append(message)
        logger.klog(
            f"#DM {self.name}({self.id}) -> {message.to}({receiver.id}): {bytes(message.body, 'latin_1').decode()}"
        )

        if hasattr(receiver, "websocket"):
            await receiver.websocket.send_json(WebsocketEvent.build_message(self.id, message))
            return True

        receiver.enqueue(await PacketBuilder.BuildMessage(self.id, message))
        return True

    async def add_spectator(self, *_) -> bool:
        return True

    async def remove_spectator(self, *_) -> bool:
        return True

    async def remove_hidden_spectator(self, *_) -> bool:
        return True

    async def say_bancho_restarting(self, delay: int = 20) -> bool:
        await self.websocket.send_json(
            WebsocketEvent.error_disconnect(f"bancho_restart:{delay * 1000}")
        )
        return True

    def enqueue(self, *_):
        return

    def dequeue(self, *_) -> bytes:
        return b""
