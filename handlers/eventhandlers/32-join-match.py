from blob import Context
from handlers.decorators import OsuEvent
from packets.Builder.index import PacketBuilder
from packets.OsuPacketID import OsuPacketID
from packets.Reader.PacketResolver import PacketResolver

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 32, bancho response: 36/37 (JoinFailed, JoinSuccess)
@OsuEvent.register_handler(OsuPacketID.Client_MatchJoin)
async def leave_match(data: bytes, token: "Player"):
    match_id, password = PacketResolver.read_mp_join_data(data)
    match = Context.matches.get(match_id, None)

    if not match:
        token.enqueue(PacketBuilder.MatchJoinFailed())
        return False

    await match.join_player(token, password)
    return True
