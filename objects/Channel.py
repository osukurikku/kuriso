from typing import List

from lib import logger
from objects.BanchoObjects import Message
from objects.constants.KurikkuPrivileges import KurikkuPrivileges
from objects.Player import Player
from packets.Builder.index import PacketBuilder


class Channel:

    def __init__(self, server_name: str = '', description: str = '', public_read: bool = False,
                       public_write: bool = False, temp_channel: bool = False):
        self.users: List[int] = []
        # for use this client should be like #osu, #admin, #osu, #specatator, #multiplayer, #lobby and etc.
        # server can store it like #banana, #spec_<id>, #multi_<id> and etc.
        self.server_name: str = server_name
        self.description: str = description
        self.can_read: bool = public_read
        self.can_write: bool = public_write
        self.temp_channel: bool = temp_channel # True if spectator or multi lobby channel

    @property
    def name(self):
        if self.server_name.startswith("#spec_"):
            return "#spectator"
        elif self.server_name.startswith("#multi_"):
            return "#multiplayer"  # don't remember that this values only OSU CLIENT, for irc we will send server name

        return self.server_name

    @staticmethod
    def is_privileged(privs: int) -> bool:
        return bool((privs & KurikkuPrivileges.Developer) == KurikkuPrivileges.Developer or \
                    (privs & KurikkuPrivileges.CM) == KurikkuPrivileges.CM or \
                    (privs & KurikkuPrivileges.ChatMod) == KurikkuPrivileges.ChatMod or \
                    (privs & KurikkuPrivileges.ReplayModerator) == KurikkuPrivileges.ReplayModerator)

    async def send_message(self, from_id: int, message: Message) -> bool:
        # handle channel message
        from blob import BlobContext
        receivers = [BlobContext.players.get_token(uid=player) for player in self.users]
        for receiver in receivers:
            if receiver.id == from_id:
                continue # ignore ourself
            receiver.enqueue(
                await PacketBuilder.BuildMessage(from_id, message)
            )
        return True

    async def join_channel(self, p: Player) -> bool:
        from blob import BlobContext
        if p.id in self.users:
            p.enqueue(await PacketBuilder.SuccessJoinChannel(self.name))
            return True

        if not self.can_read and not self.is_privileged(p.privileges):
            logger.klog(f"[{p.name}] Tried to join private channel {self.server_name} but haven't enough staff "
                        "permissions")
            return False

        # enqueue join channel
        p.enqueue(await PacketBuilder.SuccessJoinChannel(self.name))
        self.users.append(p.id)
        logger.klog(f"[{p.name}] Joined to {self.server_name}")

        # now we need update channel stats
        if self.temp_channel:
            receivers = [BlobContext.players.get_token(uid=uid) for uid in self.users]
        else:
            receivers = BlobContext.players.get_all_tokens()
        for receiver in receivers:
            receiver.enqueue(
                await PacketBuilder.UpdateChannelInfo(self)
            )
        return True

    async def leave_channel(self, p: Player) -> bool:
        from blob import BlobContext
        if p.id not in self.users:
            return False

        # enqueue leave channel
        p.enqueue(await PacketBuilder.PartChannel(self.name))
        self.users.pop(self.users.index(p.id))
        logger.klog(f"[{p.name}] Parted from {self.server_name}")

        # now we need update channel stats
        if self.temp_channel:
            receivers = [BlobContext.players.get_token(uid=uid) for uid in self.users]
        else:
            receivers = BlobContext.players.get_all_tokens()
        for receiver in receivers:
            receiver.enqueue(
                await PacketBuilder.UpdateChannelInfo(self)
            )
        return True
