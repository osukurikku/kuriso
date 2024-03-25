from handlers.decorators import OsuEvent
from objects.constants.Slots import SlotStatus
from packets.Builder.index import PacketBuilder
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 56, bancho response: update match
@OsuEvent.register_handler(OsuPacketID.Client_MatchFailed)
async def player_failed(_, token: "Player"):
    if not token.match:
        return False

    match = token.match
    slot_ind = -1
    for ind, slot in enumerate(match.slots):
        if slot.token == token:
            slot_ind = ind
            break

    match.slots[slot_ind].passed = False
    is_player_failed = PacketBuilder.MatchPlayerFailed(slot_ind)
    await match.enqueue_to_specific(is_player_failed, SlotStatus.Playing)
    return True
