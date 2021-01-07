from typing import List

from lib import logger

from objects.constants.KurikkuPrivileges import KurikkuPrivileges
from packets.Builder.index import PacketBuilder
from blob import Context

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from objects.BanchoObjects import Message
    from objects.Player import Player


class Channel:

    def __init__(self, server_name: str = '', description: str = '', public_read: bool = False,
                 public_write: bool = False, temp_channel: bool = False):
        self.users: List['Player'] = []
        # for use this client should be like #osu, #admin, #osu, #specatator, #multiplayer, #lobby and etc.
        # server can store it like #banana, #spec_<id>, #multi_<id> and etc.
        self.server_name: str = server_name
        self.description: str = description
        self.can_read: bool = public_read
        self.can_write: bool = public_write
        self.temp_channel: bool = temp_channel  # True if spectator or multi lobby channel

    @property
    def name(self):
        if self.server_name.startswith("#spec_"):
            return "#spectator"
        if self.server_name.startswith("#multi_"):
            return "#multiplayer"  # don't remember that this values only OSU CLIENT, for irc we will send server name

        return self.server_name

    @staticmethod
    def is_privileged(privs: int) -> bool:
        return bool((privs & KurikkuPrivileges.Developer) == KurikkuPrivileges.Developer or \
                    (privs & KurikkuPrivileges.CM) == KurikkuPrivileges.CM or \
                    (privs & KurikkuPrivileges.ChatMod) == KurikkuPrivileges.ChatMod or \
                    (privs & KurikkuPrivileges.ReplayModerator) == KurikkuPrivileges.ReplayModerator)

    async def send_message(self, from_id: int, message: 'Message') -> bool:
        # handle channel message
        for receiver in self.users:
            if receiver.id == from_id:
                continue  # ignore ourself

            receiver.enqueue(
                await PacketBuilder.BuildMessage(from_id, message)
            )

        message.to = self.server_name
        return True

    async def join_channel(self, p: 'Player') -> bool:
        if p in self.users:
            p.enqueue(await PacketBuilder.SuccessJoinChannel(self.name))
            return True

        if not self.can_read and not self.is_privileged(p.privileges):
            logger.klog(f"[{p.name}] Tried to join private channel {self.server_name} but haven't enough staff "
                        "permissions")
            return False

        # enqueue join channel
        p.enqueue(await PacketBuilder.SuccessJoinChannel(self.name))
        self.users.append(p)
        logger.klog(f"[{p.name}] Joined to {self.server_name}")

        # now we need update channel stats
        if self.temp_channel:
            receivers = self.users
        else:
            receivers = Context.players.get_all_tokens()
        for receiver in receivers:
            receiver.enqueue(
                await PacketBuilder.ChannelAvailable(self)
            )
        return True

    async def leave_channel(self, p: 'Player') -> bool:
        if p not in self.users:
            return False

        # enqueue leave channel
        p.enqueue(await PacketBuilder.PartChannel(self.name))
        self.users.pop(self.users.index(p))
        logger.klog(f"[{p.name}] Parted from {self.server_name}")

        # now we need update channel stats
        if self.temp_channel:
            receivers = self.users
        else:
            receivers = Context.players.get_all_tokens()
        for receiver in receivers:
            receiver.enqueue(
                await PacketBuilder.ChannelAvailable(self)
            )

        if len(self.users) < 1 and self.temp_channel:
            # clean channel because all left and channel is temp(for multi lobby or spectator)
            Context.channels.pop(self.server_name)

        return True
