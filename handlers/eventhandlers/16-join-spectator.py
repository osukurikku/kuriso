from blob import Context
from lib import logger
from packets.Reader.PacketResolver import PacketResolver
from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 16, bancho response: 42
@OsuEvent.register_handler(OsuPacketID.Client_StartSpectating)
async def join_spectator(packet_data: bytes, token: 'Player'):
    to_spectate_id = await PacketResolver.read_specatator_id(packet_data)

    player_spec = Context.players.get_token(uid=to_spectate_id)
    if not player_spec:
        logger.elog(f"{token.name} failed to spectate non-exist user with id {to_spectate_id}")
        return False

    if token.spectating:
        # remove old spectating, because we found new victim
        await token.spectating.remove_spectator(token)

    await player_spec.add_spectator(token)
    return True

