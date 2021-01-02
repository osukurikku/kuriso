from handlers.decorators import OsuEvent
from objects.constants.Modificators import Mods
from objects.constants.Slots import SlotStatus, SlotTeams
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
    if match.in_progress or slotIndex > 16 or slotIndex < 0:
        return False

    slot = match.slots[slotIndex]
    if (slot.status & SlotStatus.HasPlayer) > 0 or slot.status == SlotStatus.Locked:
        return False

    currentSlot = None
    for m_slot in match.slots:
        if m_slot.token == token:
            currentSlot = m_slot
            break

    slot.mods = currentSlot.mods
    slot.token = currentSlot.token
    slot.status = currentSlot.status
    slot.team = currentSlot.team

    currentSlot.mods = Mods.NoMod
    currentSlot.token = None
    currentSlot.status = SlotStatus.Open
    currentSlot.team = SlotTeams.Neutral

    await match.update_match()
    return True
