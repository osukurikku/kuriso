from bot.bot import CrystalBot
from handlers.decorators import OsuEvent
from lib import logger
from objects.BanchoObjects import Message
from packets.OsuPacketID import OsuPacketID
from packets.Reader.PacketResolver import PacketResolver

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 25, bancho response: 7
@OsuEvent.register_handler(OsuPacketID.Client_SendIrcMessagePrivate)
async def send_private_message(packet_data: bytes, token: "Player"):
    if token.silenced:
        logger.klog(f"<{token.name}> This bruh tried to send message, when he is muted")
        return False

    message = PacketResolver.read_message(packet_data)
    message.client_id = token.id
    message.sender = token.name
    if message.to == CrystalBot.bot_name:
        crystal_answer = await CrystalBot.proceed_command(message)
        if not crystal_answer:
            return True  # just ignore it

    await token.send_message(
        Message(
            sender=token.name,
            body=message.body,
            to=message.to,
            client_id=token.id,
        ),
    )
    return True
