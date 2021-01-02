from handlers.decorators import OsuEvent
from objects.constants.Slots import SlotStatus
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 55, bancho response: update match
@OsuEvent.register_handler(OsuPacketID.Client_MatchNotReady)
async def match_unready(_, token: 'Player'):
    if not token.match:
        return False

    match = token.match
    currentSlot = None
    for m_slot in match.slots:
        if m_slot.token == token:
            currentSlot = m_slot
            break

    currentSlot.status = SlotStatus.NotReady

    await match.update_match()
    return True
