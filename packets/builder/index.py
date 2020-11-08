from typing import Union, List

import objects.Player
from objects import Player
from packets.OsuPacketID import OsuPacketID
from packets.Reader.OsuTypes import osuTypes
from packets.Reader.index import CreateBanchoPacket


class PacketBuilder:

    # server packet: 5
    @staticmethod
    async def UserID(user_id: int) -> bytes:
        # id responses:
        # -1: authentication failed
        # -2: old client
        # -3: banned
        # -4: banned
        # -5: error occurred
        # -6: needs supporter
        # -7: password reset
        # -8: requires verification
        # ??: valid id
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_LoginReply.value,
            (user_id, osuTypes.int32)
        )

    @staticmethod
    async def MainMenuIcon(icon: str) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_TitleUpdate.value,
            (icon, osuTypes.string)
        )

    # server packet: 25
    @staticmethod
    async def Notification(message: str) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_Announce,
            (message, osuTypes.string)
        )

    # server packet: 75
    @staticmethod
    async def ProtocolVersion(version: int) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_ProtocolNegotiation.value,
            (version, osuTypes.int32)
        )

    # server packet: 71
    @staticmethod
    async def BanchoPrivileges(privs: int) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_LoginPermissions.value,
            (privs, osuTypes.int32)
        )

    # server packet: 72
    @staticmethod
    async def FriendList(friend_list: Union[List[int]]) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_FriendsList.value,
            (friend_list, osuTypes.i32_list)
        )

    # server packet: 92
    @staticmethod
    async def SilenceEnd(silence_time: int) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_BanInfo.value,
            (silence_time, osuTypes.u_int32)
        )

    # server packet: 83
    @staticmethod
    async def UserPresence(player: Player) -> bytes:
        print(player.id, type(player.id))
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_UserPresence.value,
            (player.id, osuTypes.int32),
            (player.name, osuTypes.string),
            (player.timezone, osuTypes.u_int8),
            (player.country[0], osuTypes.u_int8),
            (player.bancho_privs.value, osuTypes.u_int8),
            (player.location[0], osuTypes.float64),
            (player.location[1], osuTypes.float64),
            (player.current_stats.leaderboard_rank, osuTypes.int32)
        )

    # client packet: 3, bancho response: 11
    @staticmethod
    async def UserStats(player: Player) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_HandleOsuUpdate.value,
            (player.id, osuTypes.int32),
            (player.pr_status.action.value, osuTypes.u_int8),
            (player.pr_status.action_text, osuTypes.string),
            (player.pr_status.map_md5, osuTypes.string),
            (player.pr_status.mods.value, osuTypes.int32),
            (player.pr_status.mode.value, osuTypes.u_int8),
            (player.pr_status.map_id, osuTypes.int32),
            (player.current_stats.ranked_score, osuTypes.int64),
            (player.current_stats.accuracy/100.0, osuTypes.float32),
            (player.current_stats.total_plays, osuTypes.int32),
            (player.current_stats.total_score, osuTypes.u_int64),
            (player.current_stats.leaderboard_rank, osuTypes.int32),
            (player.current_stats.pp, osuTypes.int16)
        )