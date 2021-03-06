from handlers.decorators import OsuEvent
from objects.constants.Modificators import Mods
from packets.OsuPacketID import OsuPacketID
from packets.Reader.PacketResolver import PacketResolver

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 51, bancho response: update match
@OsuEvent.register_handler(OsuPacketID.Client_MatchChangeMods)
async def update_match_mods(packet_data: bytes, token: 'Player'):
    if not token.match:
        return False

    match = token.match
    newMods = Mods(await PacketResolver.read_mods(packet_data))
    await match.change_mods(newMods, token)

    await match.update_match()
    return True
