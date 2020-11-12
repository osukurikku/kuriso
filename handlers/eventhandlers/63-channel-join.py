import objects.Player
from blob import BlobContext
from handlers.decorators import OsuEvent
from lib import logger
from objects.Channel import Channel
from packets.OsuPacketID import OsuPacketID
from packets.Reader.PacketResolver import PacketResolver


# client packet: 63
@OsuEvent.register_handler(OsuPacketID.Client_ChannelJoin)
async def channel_join(packet_data: bytes, token: objects.Player.Player):
    chan_name = await PacketResolver.read_channel_name(packet_data)
    if not chan_name.startswith("#"):
        return

    chan: Channel = BlobContext.channels.get(chan_name, None)
    if not chan:
        logger.elog(f'[{token.name}] Failed to join in {chan_name}')
        return False

    await chan.join_channel(token)
    return True
