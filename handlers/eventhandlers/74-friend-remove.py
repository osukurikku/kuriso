from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID
from packets.Reader.PacketResolver import PacketResolver
from helpers import userHelper

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from objects.Player import Player


# Client packet: 74
@OsuEvent.register_handler(OsuPacketID.Client_FriendRemove)
async def remove_friend(packet_data: bytes, token: 'Player'):
    not_friend_id = await PacketResolver.read_friend_id(packet_data)
    await userHelper.remove_friend(token.id, not_friend_id)
    return True
