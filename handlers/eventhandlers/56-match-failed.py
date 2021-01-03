from handlers.decorators import OsuEvent
from objects.constants.Slots import SlotStatus
from packets.Builder.index import PacketBuilder
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 56, bancho response: update match
@OsuEvent.register_handler(OsuPacketID.Client_MatchFailed)
async def match_change_team(_, token: 'Player'):
    if not token.match:
        return False

    match = token.match
    slotInd = -1
    for (ind, slot) in enumerate(match.slots):
        if slot.token == token:
            slotInd = ind
            break

    player_failed = await PacketBuilder.MatchPlayerFailed(slotInd)
    await match.enqueue_to_specific(player_failed, SlotStatus.Playing)
    return True
