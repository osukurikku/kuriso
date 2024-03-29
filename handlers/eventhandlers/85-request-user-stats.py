from blob import Context
from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID
from packets.Reader.PacketResolver import PacketResolver
from packets.Builder.index import PacketBuilder

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 85, bancho response: array with 11
@OsuEvent.register_handler(OsuPacketID.Client_UserStatsRequest)
async def request_user_stats(packet_data: bytes, token: "Player"):
    data = PacketResolver.read_request_users_stats(packet_data)
    if len(data) > 32:
        return False

    for user in data:
        if user == token.id:
            # if this own id ignore
            continue
        searched_player = Context.players.get_token(uid=user)
        if searched_player and not searched_player.is_restricted:
            token.enqueue(PacketBuilder.UserStats(searched_player))

    return True
