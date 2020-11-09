import objects.Player
from blob import BlobContext
from handlers.decorators import OsuEvent
from objects.constants.GameModes import GameModes
from packets.OsuPacketID import OsuPacketID
from packets.Reader.PacketResolver import PacketResolver
from packets.Builder.index import PacketBuilder


@OsuEvent.register_handler(OsuPacketID.Client_SendUserStatus)
async def update_action(packet_data: bytes, p: objects.Player.Player):
    resolved_data = await PacketResolver.read_new_presence(packet_data)

    need_presence = False
    if GameModes(resolved_data['mode']) != p.selected_game_mode:
        # okay, we have new gamemode here. We need to send userstats and new user panel
        p.selected_game_mode = GameModes(resolved_data['mode'])
        await p.update_stats(p.selected_game_mode)

    # in this case, we should send only new stats
    p.selected_game_mode = GameModes(resolved_data['mode'])
    p.pr_status.update(**resolved_data)

    for p1 in BlobContext.players.get_all_tokens():
        data = await PacketBuilder.UserStats(p1) + \
                await PacketBuilder.UserPresence(p1)
        p1.enqueue(data)

    return True
