from handlers.decorators import OsuEvent
from packets.Builder.index import PacketBuilder
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 47, bancho response: update match
@OsuEvent.register_handler(OsuPacketID.Client_MatchScoreUpdate)
async def match_change_team(packet_data: bytes, token: 'Player'):
    if not token.match:
        return False

    match = token.match
    slotInd = -1
    for (ind, slot) in enumerate(match.slots):
        if slot.token == token:
            slotInd = ind
            break

    packet_data = bytearray(packet_data)
    packet_data[4] = slotInd

    score_updated = await PacketBuilder.MultiScoreUpdate(packet_data)
    await match.enqueue_to_all(score_updated)
    return True
