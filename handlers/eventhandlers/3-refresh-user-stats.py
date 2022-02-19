from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID
from packets.Builder.index import PacketBuilder

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 3, bancho response: 11
@OsuEvent.register_handler(OsuPacketID.Client_RequestStatusUpdate)
async def refresh_user_stats(_, token: "Player"):
    await token.update_stats()
    token.enqueue(await PacketBuilder.UserStats(token))
    return True
