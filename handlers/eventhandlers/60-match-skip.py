from handlers.decorators import OsuEvent
from objects.constants.Slots import SlotStatus
from packets.Builder.index import PacketBuilder
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 60, bancho response: update match
@OsuEvent.register_handler(OsuPacketID.Client_MatchSkipRequest)
async def match_skip(_, token: "Player"):
    if not token.match:
        return False

    match = token.match
    slot = match.get_slot(token)
    slot.skipped = True

    for slot in match.slots:
        if slot.status == SlotStatus.Playing and not slot.skipped:
            return

    match_skip_packet = PacketBuilder.MultiSkip()
    await match.enqueue_to_specific(match_skip_packet, SlotStatus.Playing)
    return True
