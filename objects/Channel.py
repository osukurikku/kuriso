from typing import List, Union

from lib import logger

from objects.constants.KurikkuPrivileges import KurikkuPrivileges
from blob import Context

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.BanchoObjects import Message
    from objects.Player import Player
    from objects.IRCPlayer import IRCPlayer


class Channel:
    def __init__(
        self,
        server_name: str = "",
        description: str = "",
        public_read: bool = False,
        public_write: bool = False,
        temp_channel: bool = False,
    ):
        self.users: List[Union["Player", "IRCPlayer"]] = []
        # for use this client should be like #osu, #admin, #osu, #specatator, #multiplayer, #lobby and etc.
        # server can store it like #banana, #spec_<id>, #multi_<id> and etc.
        self.server_name = server_name
        self.description = description
        self.can_read = public_read
        self.can_write = public_write
        self.temp_channel = temp_channel  # True if spectator or multi lobby channel

    @property
    def name(self):
        if self.server_name.startswith("#spec_"):
            return "#spectator"
        if self.server_name.startswith("#multi_"):
            return "#multiplayer"  # remember that this values only OSU CLIENT, for irc we will send server name

        return self.server_name

    @staticmethod
    def is_privileged(privs: int) -> bool:
        return bool(
            (privs & KurikkuPrivileges.Developer) == KurikkuPrivileges.Developer
            or (privs & KurikkuPrivileges.CM) == KurikkuPrivileges.CM
            or (privs & KurikkuPrivileges.ChatMod) == KurikkuPrivileges.ChatMod
            or (privs & KurikkuPrivileges.ReplayModerator) == KurikkuPrivileges.ReplayModerator,
        )

    async def send_message(self, from_id: int, message: "Message") -> bool:
        message.to = self.name
        # handle channel message
        for receiver in self.users:
            if receiver.id == from_id:
                continue  # ignore ourself

            await receiver.on_message(from_id, message, server_name=self.server_name)

        return True

    async def join_channel(self, p: Union["Player", "IRCPlayer"]) -> bool:
        if p in self.users:
            await p.on_channel_join(self.name, self.server_name)
            return True

        if not self.can_read and not self.is_privileged(p.privileges):
            logger.klog(
                f"<{p.name}> Tried to join private channel {self.server_name} but haven't enough staff "
                "permissions",
            )
            return False

        # enqueue join channel
        await p.on_channel_join(self.name, self.server_name)
        self.users.append(p)
        logger.klog(f"<{p.name}> Joined to {self.server_name}")

        # now we need update channel stats
        if self.temp_channel:
            receivers = self.users
        else:
            receivers = Context.players.get_all_tokens()
        for receiver in receivers:
            await receiver.on_channel_another_user_join(p.name, channel=self)
        return True

    async def leave_channel(self, p: Union["Player", "IRCPlayer"]) -> bool:
        if p not in self.users:
            return False

        # enqueue leave channel
        await p.on_channel_leave(self.name, self.server_name)
        self.users.pop(self.users.index(p))
        logger.klog(f"<{p.name}> Parted from {self.server_name} {len(self.users)}")

        # now we need update channel stats
        if self.temp_channel:
            receivers = self.users
        else:
            receivers = Context.players.get_all_tokens()
        for receiver in receivers:
            await receiver.on_channel_another_user_leave(p.name, channel=self)

        if len(self.users) < 1 and self.temp_channel:
            # clean channel because all left and channel is temp(for multi lobby or spectator)
            Context.channels.pop(self.server_name)

        return True
