from handlers.decorators import OsuEvent
from objects.constants.Slots import SlotTeams
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 77, bancho response: update match
@OsuEvent.register_handler(OsuPacketID.Client_MatchChangeTeam)
async def match_change_team(_, token: "Player"):
    if not token.match:
        return False

    match = token.match
    slot = match.get_slot(token)
    slot.team = SlotTeams.Blue if slot.team == SlotTeams.Red else SlotTeams.Red

    await match.update_match()
    return True
