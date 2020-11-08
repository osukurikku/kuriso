import objects.Player
from blob import BlobContext
from handlers.decorators import OsuEvent
from objects.constants.GameModes import GameModes
from packets.OsuPacketID import OsuPacketID
from packets.Reader.PacketResolver import PacketResolver
from packets.builder.index import PacketBuilder


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


'''
            'action_id': await buffer.read_byte(),
            'action_text': await buffer.read_osu_string(),
            'map_md5': await buffer.read_osu_string(),
            'mods': await buffer.read_u_int_32(),
            'mode': await buffer.read_byte(),
            'map_id': await buffer.read_int_32()

        self.action = kwargs.get('action', Action.Idle)
        self.action_text = kwargs.get('action_text', '')
        self.map_md5 = kwargs.get('map_md5', '')
        self.mode = kwargs.get('mode', GameModes.STD)
        self.mods = kwargs.get('mods', Modifications.NOMOD)
        self.map_id = kwargs.get('map_id', 0)


["actionID", dataTypes.BYTE],
    ["actionText", dataTypes.STRING],
    ["actionMd5", dataTypes.STRING],
    ["actionMods", dataTypes.UINT32],
    ["gameMode", dataTypes.BYTE],
    ["beatmapID", dataTypes.SINT32]

'''