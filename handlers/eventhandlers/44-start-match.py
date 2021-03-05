from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 44, bancho response: update match
@OsuEvent.register_handler(OsuPacketID.Client_MatchStart)
async def match_change_team(_, token: 'Player'):
    if not token.match or not (token == token.match.host_tourney or token == token.match.host):
        return False

    await token.match.start()
    return True
