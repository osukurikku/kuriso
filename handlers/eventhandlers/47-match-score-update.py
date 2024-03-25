from handlers.decorators import OsuEvent
from objects.constants.Slots import SlotStatus
from packets.Builder.index import PacketBuilder
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

from packets.Reader.index import KurisoPacketReader

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 47, bancho response: update match
@OsuEvent.register_handler(OsuPacketID.Client_MatchScoreUpdate)
async def match_score_update(packet_data: bytes, token: "Player"):
    if not token.match:
        return False

    match = token.match
    slotInd = -1
    for ind, slot in enumerate(match.slots):
        if slot.token == token:
            slotInd = ind
            break
    slot = match.slots[slotInd]

    # We need extract score and hp
    with memoryview(packet_data) as packet:
        reader = KurisoPacketReader(packet)
        reader.slice_buffer(17)
        score = reader.read_int_32()
        reader.slice_buffer(5)
        hp_points = reader.read_byte()

    slot.score = score
    slot.failed = hp_points == 254

    packet_data = bytearray(packet_data)
    packet_data[4] = slotInd

    score_updated = PacketBuilder.MultiScoreUpdate(packet_data)
    await match.enqueue_to_specific(score_updated, SlotStatus.Playing)
    return True
