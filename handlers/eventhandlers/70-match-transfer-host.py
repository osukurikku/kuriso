from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

from packets.Reader.PacketResolver import PacketResolver

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 70, bancho response: 50 for new host
@OsuEvent.register_handler(OsuPacketID.Client_MatchTransferHost)
async def transfer_host(packet_data: bytes, token: "Player"):
    if not token.match or token not in (token.match.host_tourney, token.match.host):
        return False

    match = token.match
    slot_index = PacketResolver.read_slot_index(packet_data)
    if match.in_progress or slot_index > 15 or slot_index < 0:
        return False

    await match.move_host(slot_ind=slot_index)
    return True
