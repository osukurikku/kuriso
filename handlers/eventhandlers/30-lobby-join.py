from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID
from packets.Builder.index import PacketBuilder
from blob import Context

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 30, bancho response: [Array with id: 27]
@OsuEvent.register_handler(OsuPacketID.Client_LobbyJoin)
async def refresh_user_stats(_, token: 'Player'):
    for _, match in Context.matches.items():
        token.enqueue(await PacketBuilder.NewMatch(match))

    return True