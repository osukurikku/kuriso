from lib import logger
from handlers.decorators import OsuEvent
from packets.Builder.index import PacketBuilder
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 18, bancho response: 15
@OsuEvent.register_handler(OsuPacketID.Client_SpectateFrames)
async def send_spec_frame(packet_data: bytes, token: 'Player'):
    """
        Ough, let's talk about spectator frames.
        This thing is kinda weird because we can't handle properly.
        This thing sending so frequently. We need quick handle for it!
    """
    spectator_frame = await PacketBuilder.QuickSpectatorFrame(packet_data)
    for recv in token.spectators:
        print(recv.id)
        recv.enqueue(spectator_frame)

    return True
