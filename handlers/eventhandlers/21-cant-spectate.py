from lib import logger
from handlers.decorators import OsuEvent
from packets.Builder.index import PacketBuilder
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 21, bancho response: 22
@OsuEvent.register_handler(OsuPacketID.Client_CantSpectate)
async def cant_spectate(_, token: "Player"):
    if not token.spectating:
        logger.elog(f"{token.name} sent that he can't spectate, but he is not spectating...")
        return False  # impossible condition

    packet = await PacketBuilder.CantSpectate(token.id)
    token.spectating.enqueue(packet)  # send this sweet packet lol

    for recv in token.spectating.spectators:
        recv.enqueue(packet)

    return True
