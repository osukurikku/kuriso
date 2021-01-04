from handlers.decorators import OsuEvent
from lib import logger
from objects.BanchoObjects import Message
from objects.constants.KurikkuPrivileges import KurikkuPrivileges
from packets.OsuPacketID import OsuPacketID
from packets.Reader.PacketResolver import PacketResolver
from bot.bot import CrystalBot

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 25, bancho response: 7
@OsuEvent.register_handler(OsuPacketID.Client_SendIrcMessage)
async def send_private_message(packet_data: bytes, token: 'Player'):
    if token.silenced:
        logger.klog(f"[{token.name}] This bruh tried to send message, when he is muted")
        return False

    message = await PacketResolver.read_message(packet_data)
    message.client_id = token.id
    await token.send_message(Message(
        sender=token.name,
        body=message.body,
        to=message.to,
        client_id=token.id
    ))

    if (token.privileges & KurikkuPrivileges.Donor) == KurikkuPrivileges.Donor:
        # proceed channel command if user have donor
        await CrystalBot.proceed_command(message)
    return True
