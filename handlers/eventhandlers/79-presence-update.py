import objects.Player
from handlers.decorators import OsuEvent
from lib import logger
from objects.constants.PresenceFilter import PresenceFilter
from packets.OsuPacketID import OsuPacketID

from packets.Reader.PacketResolver import PacketResolver


# client packet: 79
@OsuEvent.register_handler(OsuPacketID.Client_ReceiveUpdates)
async def presence_update(packet_data: bytes, p: objects.Player.Player):
    data = await PacketResolver.read_pr_filter(packet_data)

    if not 0 <= data < 3:
        logger.elog(f"[Player/{p.name}] Tried to set bad pr filter")
        return

    p.presence_filter = PresenceFilter(data)
