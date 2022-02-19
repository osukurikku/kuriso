from blob import Context
from handlers.decorators import OsuEvent
from lib import logger
from packets.OsuPacketID import OsuPacketID
from packets.Reader.PacketResolver import PacketResolver

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from objects.Player import Player
    from objects.Channel import Channel


# client packet: 63
@OsuEvent.register_handler(OsuPacketID.Client_ChannelJoin)
async def channel_join(packet_data: bytes, token: 'Player'):
    chan_name = await PacketResolver.read_channel_name(packet_data)
    if not chan_name.startswith("#"):
        return

    chan: 'Channel' = Context.channels.get(chan_name, None)
    if not chan:
        logger.elog(f'[{token.name}] Failed to join in {chan_name}')
        return False

    await chan.join_channel(token)
    return True
