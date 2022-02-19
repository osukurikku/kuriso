from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 33, bancho response: None
@OsuEvent.register_handler(OsuPacketID.Client_MatchPart)
async def leave_match(_, token: "Player"):
    if token.match:
        await token.match.leave_player(token)

    return True
