from handlers.decorators import OsuEvent
from lib import logger
from packets.OsuPacketID import OsuPacketID
from packets.Builder.index import PacketBuilder
from blob import Context

from typing import TYPE_CHECKING

from packets.Reader.PacketResolver import PacketResolver

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 93, bancho response: update match
@OsuEvent.register_handler(OsuPacketID.Client_SpecialMatchInfoRequest)
async def refresh_user_stats(packet_data: bytes, token: "Player"):
    if not token.is_tourneymode:
        return False  # not allow use that packet for non-tourney player

    # it's good right, but i want to fix issue that i described in TourneyPlayer.py description
    # this packet can be send only by manager, if this packet was received by player without attr additional_clients
    # in 99% it was issue that i described :D
    # in that case we should firstly switch our Player objects and than proceed request
    if not hasattr(token, "additional_clients"):
        logger.wlog("[Events] Was found bad tourney clients order. Fixing it!")
        old_token = token.token
        manager_obj = Context.players.get_token(uid=token.id)
        manager_token = manager_obj.token

        manager_obj.additional_clients.pop(
            old_token
        )  # remove our actual manager form additional clients
        token.token = manager_token  # moving manager token to additional token
        manager_obj.additional_clients[
            manager_token
        ] = token  # add this token to additional clients

        Context.players.store_by_token.pop(
            manager_token
        )  # remove our additional client from manager accounts
        manager_obj.token = old_token  # assign our pseudo additional client to manager
        Context.players.store_by_token[
            old_token
        ] = manager_obj  # store this token, like it should be

        token = manager_obj  # for next code part

    match_id = PacketResolver.read_match_id(packet_data)
    if match_id not in Context.matches:
        return False

    token.enqueue(PacketBuilder.UpdateMatch(Context.matches.get(match_id), False))
    return True
