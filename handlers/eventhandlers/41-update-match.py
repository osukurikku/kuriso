from handlers.decorators import OsuEvent
from objects.constants.Slots import SlotTeams
from objects.constants.multiplayer import MatchTeamTypes
from packets.OsuPacketID import OsuPacketID
from packets.Reader.PacketResolver import PacketResolver

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 41, bancho response: 26
@OsuEvent.register_handler(OsuPacketID.Client_MatchChangeSettings)
async def update_match(data: bytes, token: "Player"):
    if not token.match or token not in (token.match.host_tourney, token.match.host):
        return False

    new_match = PacketResolver.read_match(data)
    match = token.match

    if (
        match.beatmap_md5 != new_match["beatmap_md5"]
        or match.match_playmode != new_match["play_mode"]
        or match.match_type != new_match["match_type"]
        or match.match_scoring_type != new_match["scoring_type"]
        or match.match_team_type != new_match["team_type"]
    ):
        await match.unready_everyone()

    match.beatmap_name = new_match["beatmap_name"]
    match.beatmap_md5 = new_match["beatmap_md5"]
    match.beatmap_id = new_match["beatmap_id"]
    match.name = (
        new_match["name"] if len(new_match["name"]) > 0 else f"{match.host.name}'s game"
    )

    if match.match_team_type != new_match["team_type"]:
        if (
            new_match["team_type"] == MatchTeamTypes.TagTeamVs
            or new_match["team_type"] == MatchTeamTypes.TeamVs
        ):
            for (i, slot) in enumerate(match.slots):
                if slot.team == SlotTeams.Neutral:
                    slot.team = SlotTeams.Red if i % 2 == 1 else SlotTeams.Blue
        else:
            for slot in match.slots:
                slot.team = SlotTeams.Neutral

    match.match_type = new_match["match_type"]
    match.match_scoring_type = new_match["scoring_type"]
    match.match_team_type = new_match["team_type"]
    match.match_playmode = new_match["play_mode"]
    match.seed = new_match["seed"]

    await match.change_special_mods(new_match["match_freemod"])

    await match.update_match()
    return True
