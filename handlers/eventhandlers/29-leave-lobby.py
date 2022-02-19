from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# packet id: 29 leave lobby
@OsuEvent.register_handler(OsuPacketID.Client_LobbyPart)
async def lobby_leave(_, token: "Player"):
    token.is_in_lobby = False
    return True
