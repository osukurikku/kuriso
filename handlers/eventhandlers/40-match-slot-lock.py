from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

from packets.Reader.PacketResolver import PacketResolver

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 40, bancho response: update match
@OsuEvent.register_handler(OsuPacketID.Client_MatchLock)
async def slot_lock(packet_data: bytes, token: "Player"):
    if not token.match or token not in (token.match.host_tourney, token.match.host):
        return False

    match = token.match
    slot_index = PacketResolver.read_slot_index(packet_data)
    if match.in_progress or slot_index > 15 or slot_index < 0:
        return False

    slot = match.slots[slot_index]
    if slot.token in (match.host, match.host_tourney):
        return

    slot.toggle_slot()
    await match.update_match()
    return True
