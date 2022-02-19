from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID
from packets.Reader.PacketResolver import PacketResolver
from helpers import userHelper

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# Client packet: 73
@OsuEvent.register_handler(OsuPacketID.Client_FriendAdd)
async def add_friend(packet_data: bytes, token: "Player"):
    new_friend_id = await PacketResolver.read_friend_id(packet_data)
    await userHelper.add_friend(token.id, new_friend_id)
    return True
