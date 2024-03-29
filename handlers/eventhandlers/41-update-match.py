from handlers.decorators import OsuEvent
from objects.constants.Modificators import Mods
from objects.constants.Slots import SlotTeams, SlotStatus
from objects.constants.multiplayer import MatchTeamTypes, MultiSpecialModes
from packets.OsuPacketID import OsuPacketID
from packets.Reader.PacketResolver import PacketResolver

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 41, bancho response: 26
@OsuEvent.register_handler(OsuPacketID.Client_MatchChangeSettings)
async def update_match(data: bytes, token: 'Player'):
    if not token.match or not (token == token.match.host_tourney or token == token.match.host):
        return False

    newMatch = await PacketResolver.read_match(data)
    match = token.match

    if match.beatmap_md5 != newMatch['beatmap_md5'] or \
            match.match_playmode != newMatch['play_mode'] or \
            match.match_type != newMatch['match_type'] or \
            match.match_scoring_type != newMatch['scoring_type'] or \
            match.match_team_type != newMatch['team_type']:
        await match.unready_everyone()

    match.beatmap_name = newMatch['beatmap_name']
    match.beatmap_md5 = newMatch['beatmap_md5']
    match.beatmap_id = newMatch['beatmap_id']
    match.name = newMatch['name'] if len(newMatch['name']) > 0 else f"{match.host.name}'s game"

    if match.match_team_type != newMatch['team_type']:
        if newMatch['team_type'] == MatchTeamTypes.TagTeamVs or newMatch['team_type'] == MatchTeamTypes.TeamVs:
            for (i, slot) in enumerate(match.slots):
                if slot.team == SlotTeams.Neutral:
                    slot.team = SlotTeams.Red if i % 2 == 1 else SlotTeams.Blue
        else:
            for slot in match.slots:
                slot.team = SlotTeams.Neutral

    match.match_type = newMatch['match_type']
    match.match_scoring_type = newMatch['scoring_type']
    match.match_team_type = newMatch['team_type']
    match.match_playmode = newMatch['play_mode']
    match.seed = newMatch['seed']

    await match.change_special_mods(newMatch['match_freemod'])

    await match.update_match()
    return True
