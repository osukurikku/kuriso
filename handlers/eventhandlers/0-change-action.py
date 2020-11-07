import objects.Token
from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID


@OsuEvent.register_handler(OsuPacketID.Client_RequestStatusUpdate)
async def update_action(packet_data: bytes, token: objects.Token.Token):
    print("handle change action :sip: not enough class ")
    return True
