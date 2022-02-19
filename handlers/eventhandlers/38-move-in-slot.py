from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

from packets.Reader.PacketResolver import PacketResolver

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 38, bancho response: update match
@OsuEvent.register_handler(OsuPacketID.Client_MatchChangeSlot)
async def move_in_slot(packet_data: bytes, token: 'Player'):
    if not token.match:
        return False

    match = token.match
    slotIndex = await PacketResolver.read_slot_index(packet_data)
    if match.in_progress or slotIndex > 15 or slotIndex < 0 or match.is_locked:
        return False

    await match.change_slot(token, slotIndex)
    return True
