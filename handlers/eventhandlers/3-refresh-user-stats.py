import objects.Player
from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID
from packets.builder.index import PacketBuilder


# client packet: 3, bancho response: 11
@OsuEvent.register_handler(OsuPacketID.Client_RequestStatusUpdate)
async def update_action(packet_data: bytes, token: objects.Player.Player):
    token.enqueue(await PacketBuilder.UserStats(token))
    return True
