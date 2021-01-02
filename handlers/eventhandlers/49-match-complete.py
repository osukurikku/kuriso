from handlers.decorators import OsuEvent
from objects.constants.Slots import SlotStatus
from packets.Builder.index import PacketBuilder
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 49, bancho response: update match
@OsuEvent.register_handler(OsuPacketID.Client_MatchComplete)
async def match_change_team(_, token: 'Player'):
    if not token.match:
        return False

    match = token.match
    currentSlot = None
    for m_slot in match.slots:
        if m_slot.token == token:
            currentSlot = m_slot
            break

    currentSlot.status = SlotStatus.Complete
    if any([s.status == SlotStatus.Playing for s in match.slots]):
        return

    await match.unready_completed()
    match.in_progress = False

    packet_complete = await PacketBuilder.MatchFinished()
    await match.enqueue_to_all(packet_complete)
    await match.update_match()
    return True
