import objects.Player
from handlers.decorators import OsuEvent
from lib import logger
from objects.BanchoObjects import Message
from packets.OsuPacketID import OsuPacketID
from packets.Reader.PacketResolver import PacketResolver


# client packet: 25, bancho response: 7
@OsuEvent.register_handler(OsuPacketID.Client_SendIrcMessagePrivate)
async def send_private_message(packet_data: bytes, token: objects.Player.Player):
    if token.silenced:
        logger.klog(f"[{token.name}] This bruh tried to send message, when he is muted")
        return False

    message = await PacketResolver.read_message(packet_data)
    await token.send_message(Message(
        sender=token.name,
        body=message.body,
        to=message.to,
        client_id=token.id
    ))
    return True

