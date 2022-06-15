from handlers.decorators import OsuEvent
from objects.constants.GameModes import GameModes
from packets.OsuPacketID import OsuPacketID
from packets.Reader.PacketResolver import PacketResolver
from packets.Builder.index import PacketBuilder

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


@OsuEvent.register_handler(OsuPacketID.Client_SendUserStatus)
async def update_action(packet_data: bytes, p: "Player"):
    resolved_data = PacketResolver.read_new_presence(packet_data)

    if GameModes(resolved_data["mode"]) != p.selected_game_mode:
        # okay, we have new gamemode here. We need to send userstats and new user panel
        p.selected_game_mode = GameModes(resolved_data["mode"])
        await p.update_stats(p.selected_game_mode)

    # in this case, we should send only new stats
    p.selected_game_mode = GameModes(resolved_data["mode"])
    p.pr_status.update(**resolved_data)

    data = PacketBuilder.UserStats(p) + PacketBuilder.UserPresence(p)
    p.enqueue(data)
    for spec in p.spectators:
        spec.enqueue(data)

    return True
