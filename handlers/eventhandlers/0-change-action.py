import objects.Player
from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID


@OsuEvent.register_handler(OsuPacketID.Client_RequestStatusUpdate)
async def update_action(packet_data: bytes, token: objects.Player.Player):
    print("handle change action :sip: not enough class ")
    return True
