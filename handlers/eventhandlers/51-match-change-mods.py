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
    if not token.match or not (token == token.match.host_tourney or token == token.match.host):
        return False

    match = token.match
    newMods = Mods(await PacketResolver.read_mods(packet_data))
    await match.change_mods(newMods)

    await match.update_match()
    return True
