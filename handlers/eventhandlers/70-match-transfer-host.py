from handlers.decorators import OsuEvent
from packets.Builder.index import PacketBuilder
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

from packets.Reader.PacketResolver import PacketResolver

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 70, bancho response: 50 for new host
@OsuEvent.register_handler(OsuPacketID.Client_MatchTransferHost)
async def transfer_host(packet_data: bytes, token: 'Player'):
    if not token.match or not (token == token.match.host_tourney or token == token.match.host):
        return False

    match = token.match
    slotIndex = await PacketResolver.read_slot_index(packet_data)
    if match.in_progress or slotIndex > 15 or slotIndex < 0:
        return False

    await match.move_host(slot_ind=slotIndex)
    return True
