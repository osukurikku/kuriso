from blob import Context
from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID
from packets.Builder.index import PacketBuilder

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 85, bancho response: array with 11
@OsuEvent.register_handler(OsuPacketID.Client_UserPresenceRequestAll)
async def request_user_stats(_, token: "Player"):
    for user in Context.players.get_all_tokens(ignore_tournament_clients=True):
        if not user.is_restricted:
            token.enqueue(PacketBuilder.UserPresence(user))

    return True
