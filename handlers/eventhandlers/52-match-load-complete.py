from handlers.decorators import OsuEvent
from objects.constants.Slots import SlotStatus
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 54, bancho response: update match
@OsuEvent.register_handler(OsuPacketID.Client_MatchLoadComplete)
async def match_no_beatmap(_, token: 'Player'):
    if not token.match:
        return False

    match = token.match
    match.need_load -= 1
    if match.need_load == 0:
        '''
            Start game
        '''
        await match.all_players_loaded()

    return True
