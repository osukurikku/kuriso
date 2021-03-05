from handlers.decorators import OsuEvent
from objects.Channel import Channel
from objects.Multiplayer import Match
from packets.Builder.index import PacketBuilder
from packets.OsuPacketID import OsuPacketID
from blob import Context
from packets.Reader.PacketResolver import PacketResolver

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from objects.TypedDicts import TypedReadMatch
    from objects.Player import Player


# client packet: 31, bancho response:
@OsuEvent.register_handler(OsuPacketID.Client_MatchCreate)
async def create_match(packet_data: bytes, token: 'Player'):
    match_object: 'TypedReadMatch' = await PacketResolver.read_match(packet_data)

    if not match_object['password']:
        match_object['password'] = None

    # Make match object
    match = Match(
        id=Context.matches_id,
        name=match_object['name'],
        password=match_object['password'],
        host=Context.players.get_token(uid=match_object['host_id'])
    )
    Context.matches_id += 1  # increment match id
    match.beatmap_name = match_object['beatmap_name']
    match.beatmap_md5 = match_object['beatmap_md5']
    match.beatmap_id = match_object['beatmap_id']

    match.mods = match_object['mods']
    match.seed = match_object['seed']

    match.match_type = match_object['match_type']
    match.match_playmode = match_object['play_mode']
    match.match_scoring_type = match_object['scoring_type']
    match.match_team_type = match_object['team_type']
    match.match_freemod = match_object['match_freemod']

    match.slots = match_object['slots']

    # Create match temp channel
    match_channel = Channel(
        server_name=f"#multi_{match.id}",
        description=f"Channel for #multi_{match.id}",
        public_read=True,
        public_write=True,
        temp_channel=True
    )

    # Register that channel and match
    Context.channels[f"#multi_{match.id}"] = match_channel
    match.channel = match_channel
    Context.matches[match.id] = match

    await match.join_player(token, match_object['password'])  # allow player to join match

    info_packet = await PacketBuilder.NewMatch(match)
    for user in Context.players.get_all_tokens(ignore_tournament_clients=True):
        if not user.is_in_lobby:
            continue
        if user == token:
            continue  # ignore us, because we will receive it first
        user.enqueue(info_packet)

    return True
