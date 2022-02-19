from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID
from blob import Context

from typing import TYPE_CHECKING

from packets.Reader.PacketResolver import PacketResolver

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 108, bancho response: join channel
@OsuEvent.register_handler(OsuPacketID.Client_SpecialJoinMatchChannel)
async def join_tourney_channel(packet_data: bytes, token: "Player"):
    if not token.is_tourneymode:
        return False  # not allow use that packet for non-tourney player

    match_id = await PacketResolver.read_match_id(packet_data)
    if match_id not in Context.matches:
        return False

    await Context.matches.get(match_id).channel.join_channel(token)
    token.id_tourney = match_id
    return True
