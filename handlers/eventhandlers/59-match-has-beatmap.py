from handlers.decorators import OsuEvent
from objects.constants.Slots import SlotStatus
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 59, bancho response: update match
@OsuEvent.register_handler(OsuPacketID.Client_MatchHasBeatmap)
async def match_has_beatmap(_, token: "Player"):
    if not token.match:
        return False

    match = token.match
    slot = match.get_slot(token)
    slot.status = SlotStatus.NotReady

    await match.update_match()
    return True
