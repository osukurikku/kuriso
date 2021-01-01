from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

from packets.Reader.PacketResolver import PacketResolver

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 90, bancho response:
@OsuEvent.register_handler(OsuPacketID.Client_MatchChangePassword)
async def update_password(packet_data: bytes, token: 'Player'):
    if not token.match:
        return False

    match = token.match
    newMatch = await PacketResolver.read_match(packet_data)
    if not newMatch['password']:
        match.password = None
    else:
        match.password = newMatch['password']

    await match.update_match()
    return True
