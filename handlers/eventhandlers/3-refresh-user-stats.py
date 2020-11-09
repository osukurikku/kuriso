import objects.Player
from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID
from packets.Builder.index import PacketBuilder


# client packet: 3, bancho response: 11
@OsuEvent.register_handler(OsuPacketID.Client_RequestStatusUpdate)
async def refresh_user_stats(packet_data: bytes, token: objects.Player.Player):
    await token.update_stats()
    token.enqueue(await PacketBuilder.UserStats(token))
    return True
