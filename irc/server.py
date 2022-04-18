import asyncio, time
import re
import traceback
from typing import TYPE_CHECKING

from sentry_sdk import capture_exception

from blob import Context
from bot.bot import CrystalBot
from helpers import userHelper
from lib import logger
from objects.IRCPlayer import IRCPlayer
from objects.constants import Privileges
from packets.Builder.index import PacketBuilder
from objects.BanchoObjects import Message

if TYPE_CHECKING:
    from objects.Player import Player

NAME = "kuriso!irc"
WHITE_SPACE = re.compile(r"\r?\n")

# Custom Bancho IRC exception.
class BanchoIRCException(Exception):
    """Custom expection."""

    def __init__(self, code_error: int, error: str):
        self.code: int = code_error
        self.error: str = error

    def __str__(self):
        return repr(self.error)


class IRCClient:
    def __init__(
            self,
            writer: asyncio.StreamWriter = None
         ):
        self.writer = writer

        self.ping_time: int = int(time.time())
        self.queue: bytearray = bytearray()
        self.is_authenticated: bool = False
        self.player_instance: 'Player' = None
        self.is_closing: bool = False

    def __str__(self):
        return f"{self.player_instance.name}@{NAME}"

    def dequeue(self):
        buffer = self.queue
        self.queue = bytearray()
        return buffer

    def add_queue(self, message: str):
        self.writer.write((message + "\r\n").encode())

    async def login(self, irc_token: str = ""):
        r1 = await Context.mysql.fetch(
            "SELECT irc_tokens.userid, irc_tokens.token, users.username FROM irc_tokens INNER JOIN users ON users.id = irc_tokens.userid WHERE token = %s",
            [irc_token],
        )

        if not r1:
            raise BanchoIRCException(464, f"PASS :Password incorrect")

        start_data = await userHelper.get_start_user(r1["username"])
        if not start_data:
            # await websocket.send_json(WebsocketEvent.error_disconnect("server error uwu"))
            logger.elog(
                f"[rejected/{start_data['username']}] Was attempt to connect irc!chat but server returned nothin data for stats"
            )
            self.add_queue("ERROR :Server error uwu!")
            return False

        # checking for user correct privileges at least equals 3 (NORMAL|PUBLIC)
        is_user_valid = (
                start_data["privileges"] & Privileges.USER_PUBLIC
                and start_data["privileges"] & Privileges.USER_NORMAL
        )

        if not is_user_valid:
            logger.elog(f"[rejected/{start_data['username']}] Restricted. Attempt to irc!chat")
            self.add_queue("ERROR :Bro, restricted users aren't allowed to use irc chat!")
            return False

        pToken = Context.players.get_token(uid=start_data["id"])
        if hasattr(pToken, "irc"):
            logger.elog(
                f"[{pToken.token}/{start_data['username']}] was already connected to irc! chat. Disconnecting!"
            )
            await pToken.logout()
            pToken = None

        socket_ip = self.writer.get_extra_info('peername')[0]

        player = None
        start_params = {
            "user_id": int(start_data["id"]),
            "user_name": start_data["username"],
            "privileges": start_data["privileges"],
            "utc_offset": 0,
            "pm_private": False,
            "silence_end": 0
            if start_data["silence_end"] - int(time.time()) < 0
            else start_data["silence_end"] - int(time.time()),
            "is_tourneymode": True,
            "ip": socket_ip,
            "irc": self,
        }
        if pToken and pToken.is_tourneymode:
            # check if clients have correct order
            if not hasattr(pToken, "additional_clients"):
                self.add_queue("ERROR :We have detected wrong tourney clients ordering! Wait a minute, and try again!")
                return False

            # AND WE'RE READY TO GO!
            player = IRCPlayer(**start_params)
            pToken.add_additional_client(player, player.token)
        elif pToken:
            logger.elog(
                f"[{pToken.token}/{start_data['username']}] attempt to connect to irc!chat, but logged in osu!"
            )
            return False
        else:
            # AND WE'RE READY TO GO!
            player = IRCPlayer(**start_params)
            Context.players.add_token(player)

        for p in Context.players.get_all_tokens():
            if p.is_restricted:
                continue

            p.enqueue(
                bytes(
                    await PacketBuilder.UserPresence(player) + await PacketBuilder.UserStats(player)
                )
            )

        await asyncio.gather(
            *[
                player.parse_friends(),
                player.update_stats(),
                player.parse_country(),
            ]
        )
        logger.klog(f"[{player.token}/{start_data['username']}] logged in, through irc!chat")

        self.player_instance = player
        self.is_authenticated = True
        return True

    def receive_message(self, message: 'Message'):
        irc_body = message.body.split("\n")
        for crcf in irc_body:
            self.add_queue(f":{message.sender} PRIVMSG {message.to} {crcf}")
        return True

    async def data_received(self, data):
        message = data.decode("utf-8")
        try:
            client_data = WHITE_SPACE.split(message)[:-1]
            for cmd in client_data:
                if len(cmd) > 0:
                    command, args = cmd.split(" ", 1)
                else:
                    command, args = (cmd, "")

                if command == "CAP":
                    continue

                if not self.is_authenticated:
                    if command == "PASS":
                        login_result = await self.login(args)
                        if login_result:
                            self.add_queue(
                                f":{NAME} 001 {self.player_instance.name} :Welcome to the Internet Relay Network {str(self)}!")
                            self.add_queue(f":{NAME} 251 :There are 1 users and 0 services on 1 server")
                            self.add_queue(f":{NAME} 375 :- {NAME} Message of the day -")
                            self.add_queue(f":{NAME} 372 {self.player_instance.name} :- {int(time.time())}")
                            for line in Context.motd.split("\n"):
                                self.add_queue(f":{NAME} 372 {self.player_instance.name} :{line}")
                            self.add_queue(f":{NAME} 376 :End of MOTD command")
                            continue

                    raise BanchoIRCException(464, f"{command} :Password incorrect")

                handler = getattr(self, f"handler_{command.lower()}", None)
                if not handler:
                    raise BanchoIRCException(421, f"{command} :Unknown Command!")

                await handler(args)
        except BanchoIRCException as e:
            self.writer.write(f":{NAME} {e.code} {e.error}\r\n".encode())
        except Exception as e:
            self.writer.write(f":{NAME} ERROR {repr(e)}".encode())
            capture_exception(e)
            traceback.print_exc()

    async def handler_ping(self, _):
        self.player_instance.last_packet_unix = int(time.time())
        self.add_queue(f":{NAME} PONG :{NAME}")

    async def handler_privmsg(self, args):
        channel, msg = args.split(" :", 1)
        message = Message(
            sender=self.player_instance.name,
            to=channel,
            body=msg,
            client_id=self.player_instance.id
        )
        if channel == CrystalBot.bot_name:
            await CrystalBot.proceed_command(message)
            return

        if channel.startswith("#"):
            await CrystalBot.proceed_command(message)
        await self.player_instance.send_message(message)

    async def handler_join(self, channel_list: str):
        for ch in channel_list.split(","):
            chan = Context.channels.get(ch, None)

            if not chan:
                raise BanchoIRCException(403, f"{ch} :No channel named {ch} has been found!")

            await chan.join_channel(self.player_instance)

            self.add_queue(f":Unknown TOPIC {chan.server_name} :{chan.description}")
            nicks = " ".join([client.name for client in chan.users])
            self.add_queue(f":{NAME} 353 {self.player_instance.name} = {chan.server_name} :{nicks}")
            self.add_queue(f":{NAME} 366 {self.player_instance.name} {chan.server_name} :End of /NAMES list")

    async def handler_part(self, after_part: str):
        channel = after_part.split(" ", 1)[0]
        chan = Context.channels.get(channel, None)
        if self.player_instance in chan.users:
            if not chan:
                pass

            await chan.leave_channel(self.player_instance)
        else:
            self.add_queue(f":{NAME} 403 {channel} {channel}")

    async def handler_quit(self, _):
        logger.elog(
            f"[{self.player_instance.token}/{self.player_instance.name}] Disconnected from irc!."
        )
        await self.player_instance.logout()
        self.is_closing = True

    async def connection_lost(self) -> None:
        if self.player_instance:
            await self.player_instance.logout()

    async def handler_nick(self, _):
        ...

    async def handler_user(self, _):
        ...

    async def handler_who(self, _):
        ...

    async def handler_mode(self, _):
        ...


async def IRCStreamsServer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    client = IRCClient(writer)
    try:
        while True:
            dequeue = client.dequeue()
            if dequeue:
                writer.write(dequeue)

            if client.is_closing:
                break

            data = await reader.read(1024)
            await client.data_received(data)

            await writer.drain()
    except ConnectionResetError:
        ...
    finally:
        await client.connection_lost()
