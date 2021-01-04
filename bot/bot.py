import asyncio
import os
import sys
import time
import traceback
from typing import Callable, Dict, List, TYPE_CHECKING, Optional, Union

from objects.BanchoObjects import Message
from blob import Context
from lib import logger
from objects.constants.KurikkuPrivileges import KurikkuPrivileges
from packets.Builder.index import PacketBuilder
import shlex
from objects.BotPlayer import BotPlayer

if TYPE_CHECKING:
    from objects.Player import Player


class CrystalBot:
    token: Optional['Player'] = None
    is_connected: bool = False
    connected_time: int = -1
    commands: Dict[str, Callable] = {}
    bot_id: int = 999
    bot_name: str = ""
    cd: Dict[int, int] = {}
    cool_down: int = 2  # 2 secs before executing next command

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(CrystalBot, cls).__new__(cls)

        return cls.instance

    @classmethod
    async def connect(cls) -> bool:
        if Context.players.get_token(uid=cls.bot_id):
            return False

        bot_name = await Context.mysql.fetch(
            "select username from users where id = %s",
            [cls.bot_id]
        )
        if not bot_name:
            return False
        bot_name = bot_name['username']

        cls.bot_name = bot_name
        token = BotPlayer(cls.bot_id, cls.bot_name, KurikkuPrivileges.CM.value, is_bot=True)
        Context.players.add_token(token)

        await asyncio.gather(*[
            token.parse_friends(),
            token.update_stats(),
            token.parse_country()  # we don't needed ip, we are bots
        ])

        uPanel = await PacketBuilder.UserPresence(token)
        uStats = await PacketBuilder.UserStats(token)
        for user in Context.players.get_all_tokens():
            user.enqueue(uPanel)
            user.enqueue(uStats)

        cls.token = token
        cls.connected_time = int(time.time())

    @classmethod
    def load_commands(cls) -> bool:
        sys.path.insert(0, 'bot')
        sys.path.insert(0, 'bot/commands')
        folder_files = os.listdir("bot/commands")

        for file in folder_files:
            if file.endswith(".py"):
                logger.slog(f"[Bot commands] command with {file} loaded! ")
                sys.path.insert(0, f"bot/commands/{file}")
                __import__(os.path.splitext(file)[0], None, None, [''])

        return True

    @classmethod
    def register_command(cls, command: str, aliases: Optional[List[str]] = None) -> Callable:
        """
            Decorator for registering command
        """

        if aliases is None:
            aliases = []

        def wrapper(func: Callable):
            cls.commands[command] = func
            for alias in aliases:
                cls.commands[alias] = func

        return wrapper

    @classmethod
    def check_perms(cls, need_perms: KurikkuPrivileges = KurikkuPrivileges.Normal) -> Callable:
        """
            Additional decorator to check permissions
        """

        def wrapper(func: Callable):
            async def wrapper_func(args: List[str], player: 'Player') -> str:
                if (need_perms.value & player.privileges) != need_perms.value:
                    return await func(args, player)
                else:
                    return ""

            return wrapper_func

        return wrapper

    @classmethod
    async def proceed_command(cls, message: 'Message') -> Union[bool]:
        if message.sender == cls.bot_name:
            return False

        sender = Context.players.get_token(uid=message.client_id)
        if not sender:
            return False

        text_sheet = shlex.split(message.body.replace("'", "\\'").replace('"', '\\"'), posix=True)
        comand = text_sheet[0]
        args = text_sheet[1:]

        func_comand = cls.commands.get(comand, None)
        if not func_comand:
            logger.printColored(f"[Bot] {sender.name} trying to call unknown command {comand}", logger.PINK)
            return False

        cdUser = cls.cd.get(sender.id, None)
        nowTime = int(time.time())
        if cdUser:
            if nowTime - cdUser <= cls.cool_down:  # Checking users cooldown
                cls.cd[sender.id] = nowTime
                return False

            cls.cd[sender.id] = nowTime
        else:  # If user not write something after bot running
            cls.cd[sender.id] = nowTime

        result = None
        try:
            result = await func_comand(args, sender)
        except Exception:
            logger.elog(f"[Bot] {sender.name} with {comand} crashed {args}")
            traceback.print_exc()

        msg_to_send = None
        if not result:
            msg_to_send = Message(
                sender=cls.token.name,
                body='Command crashed, write to KotRik!!!',
                to=message.sender,
                client_id=cls.token.id
            )
        else:
            msg_to_send = Message(sender=cls.token.name,
                                  body=result,
                                  to=message.to if message.to.startswith("#") else message.sender,
                                  client_id=cls.token.id)

        await cls.token.send_message(msg_to_send)
        return True
