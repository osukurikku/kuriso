from handlers.decorators import OsuEvent
from objects.constants.Modificators import Mods
from objects.constants.Slots import SlotStatus, SlotTeams
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

from packets.Reader.PacketResolver import PacketResolver

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 40, bancho response: update match
@OsuEvent.register_handler(OsuPacketID.Client_MatchLock)
async def slot_lock(packet_data: bytes, token: 'Player'):
    if not token.match or not (token == token.match.host_tourney or token == token.match.host):
        return False

    match = token.match
    slotIndex = await PacketResolver.read_slot_index(packet_data)
    if match.in_progress or slotIndex > 16 or slotIndex < 0:
        return False

    slot = match.slots[slotIndex]
    if slot.token == match.host or slot.token == match.host_tourney:
        return

    slot.toggle_slot()
    await match.update_match()
    return True
