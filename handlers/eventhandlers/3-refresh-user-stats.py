import objects.Token
from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID
from packets.builder.index import PacketBuilder


# client packet: 3, bancho response: 11
@OsuEvent.register_handler(OsuPacketID.Client_RequestStatusUpdate)
async def update_action(packet_data: bytes, token: objects.Token.Token):
    token.enqueue(await PacketBuilder.RefreshUserStats(token))
    return True
