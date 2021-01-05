from typing import Union, List, TYPE_CHECKING

from packets.OsuPacketID import OsuPacketID
from packets.Reader.OsuTypes import osuTypes
from packets.Reader.index import CreateBanchoPacket

if TYPE_CHECKING:
    from objects import Player
    from objects.Multiplayer import Match
    from objects.BanchoObjects import Message


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
    async def UserPresence(player: 'Player') -> bytes:
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
    async def UserStats(player: 'Player') -> bytes:
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
            (player.current_stats.accuracy / 100.0, osuTypes.float32),
            (player.current_stats.total_plays, osuTypes.int32),
            (player.current_stats.total_score, osuTypes.u_int64),
            (player.current_stats.leaderboard_rank, osuTypes.int32),
            (player.current_stats.pp, osuTypes.int16)
        )

    # client packet: 2, bancho response: 12
    @staticmethod
    async def Logout(uid: int) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_HandleUserQuit.value,
            (uid, osuTypes.int32),
            (0, osuTypes.u_int8)
        )

    # bancho response: 64
    @staticmethod
    async def SuccessJoinChannel(name: str) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_ChannelJoinSuccess.value,
            (name, osuTypes.string)
        )

    @staticmethod
    async def ErrorJoinChannel(name: str) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_ChannelJoinSuccess.value,
            (name, osuTypes.string)
        )

    # bancho response: 66
    @staticmethod
    async def PartChannel(name: str) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_ChannelRevoked.value,
            (name, osuTypes.string)
        )

    @staticmethod
    async def UpdateChannelInfo(channel) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_ChannelAvailable.value,
            (channel.name, osuTypes.string),
            (channel.description, osuTypes.string),
            (len(channel.users), osuTypes.int16),
        )

    # bancho response: 7
    @staticmethod
    async def BuildMessage(uid: int, message: 'Message') -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_SendMessage.value,
            (message.sender, osuTypes.string),
            (message.body, osuTypes.string),
            (message.to, osuTypes.string),
            (uid, osuTypes.int32)
        )

    # bancho response: 65
    @staticmethod
    async def ChannelAvailable(channel) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_ChannelAvailable.value,
            (channel.name, osuTypes.string),
            (channel.description, osuTypes.string),
            (len(channel.users), osuTypes.int16)
        )

    # bancho response: 89
    @staticmethod
    async def ChannelListeningEnd() -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_ChannelListingComplete.value
        )

    # bancho response: 100
    @staticmethod
    async def PMBlocked(target: str) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_UserPMBlocked.value,
            ('', osuTypes.string),
            ('', osuTypes.string),
            (target, osuTypes.string),
            (0, osuTypes.int32)
        )

    # bancho response: 101
    @staticmethod
    async def TargetSilenced(target: str) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_TargetIsSilenced.value,
            ('', osuTypes.string),
            ('', osuTypes.string),
            (target, osuTypes.string),
            (0, osuTypes.int32)
        )

    # bancho response: 42
    @staticmethod
    async def FellowSpectatorJoined(uid: int) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_FellowSpectatorJoined.value,
            (uid, osuTypes.int32)
        )

    # bancho response: 13
    @staticmethod
    async def SpectatorJoined(uid: int) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_SpectatorJoined.value,
            (uid, osuTypes.int32)
        )

    # bancho response: 43
    @staticmethod
    async def FellowSpectatorLeft(uid: int) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_FellowSpectatorLeft.value,
            (uid, osuTypes.int32)
        )

    # bancho response: 14
    @staticmethod
    async def SpectatorLeft(uid: int) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_SpectatorLeft.value,
            (uid, osuTypes.int32)
        )

    # bancho response: 22
    @staticmethod
    async def CantSpectate(uid: int) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_SpectatorCantSpectate.value,
            (uid, osuTypes.int32)
        )

    # bancho response: 15
    @staticmethod
    async def QuickSpectatorFrame(data: bytes) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_SpectateFrames.value,
            (data, osuTypes.raw)
        )

    # bancho response: 26
    @staticmethod
    async def UpdateMatch(match: 'Match', send_pw: bool = True) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_MatchUpdate.value,
            ((match, send_pw), osuTypes.match)
        )

    # bancho response: 27
    @staticmethod
    async def NewMatch(match: 'Match') -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_MatchNew.value,
            ((match, False), osuTypes.match)
        )

    # bancho response: 36
    @staticmethod
    async def MatchJoinSuccess(match: 'Match') -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_MatchJoinSuccess.value,
            ((match, True), osuTypes.match)
        )

    # bancho response: 37
    @staticmethod
    async def MatchJoinFailed() -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_MatchJoinFail.value
        )

    # bancho response: 46
    @staticmethod
    async def InitiateStartMatch(match: 'Match') -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_MatchStart.value,
            ((match, True), osuTypes.match)
        )

    # bancho response: 28
    @staticmethod
    async def DisbandMatch(match: 'Match') -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_MatchDisband.value,
            (match.id, osuTypes.int32)
        )

    # bancho response: 50
    @staticmethod
    async def MatchHostTransfer() -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_MatchTransferHost.value
        )

    # bancho response: 61
    @staticmethod
    async def MultiSkip():
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_MatchSkip.value
        )

    # bancho response: 53
    @staticmethod
    async def AllPlayersLoaded():
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_MatchAllPlayersLoaded.value
        )

    # bancho response: 48
    @staticmethod
    async def MultiScoreUpdate(packet_data: bytearray) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_MatchScoreUpdate.value,
            (packet_data, osuTypes.raw)
        )

    # bancho response: 58
    @staticmethod
    async def MatchFinished() -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_MatchComplete.value
        )

    # bancho response: 57
    @staticmethod
    async def MatchPlayerFailed(slot_ind: int) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_MatchPlayerFailed.value,
            (slot_ind, osuTypes.int16),
        )

    # bancho response: 94
    @staticmethod
    async def UserSilenced(user_id: int) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_UserSilenced.value,
            (user_id, osuTypes.u_int32)
        )

    # bancho response: 104
    @staticmethod
    async def UserRestricted() -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_AccountRestricted.value
        )
