import struct
from typing import Union, List, TYPE_CHECKING, Tuple, Any

from objects.constants.Slots import SlotStatus
from packets.OsuPacketID import OsuPacketID
from packets.Reader.OsuTypes import osuTypes


if TYPE_CHECKING:
    from objects import Player
    from objects.Multiplayer import Match
    from objects.BanchoObjects import Message


class KurisoPacketWriter:

    def __init__(self):
        self.buffer = b""

    def get_string(self) -> bytes:
        return self.buffer

    def write_to_buffer(self, value: Union[bytes, bytearray]):
        self.buffer = self.buffer + value
        return True

    def write_u_int(self, value: int, byte_length: int) -> bool:
        self.buffer = self.buffer + value.to_bytes(
            byte_length, byteorder="little", signed=False
        )
        return True

    def write_int(self, value: int, byte_length: int) -> bool:
        self.buffer = self.buffer + value.to_bytes(byte_length, byteorder="little", signed=True)
        return True

    def write_byte(self, value: int) -> bool:
        return self.write_u_int(value, 1)

    def write_bytes(self, value: Union[Tuple, List]):
        return self.write_to_buffer(bytearray(value))

    def write_u_int_8(self, value: int) -> bool:
        return self.write_u_int(value, 1)

    def write_int_8(self, value: int) -> bool:
        return self.write_int(value, 1)

    def write_u_int_16(self, value: int) -> bool:
        return self.write_u_int(value, 2)

    def write_int_16(self, value: int) -> bool:
        return self.write_int(value, 2)

    def write_u_int_32(self, value: int) -> bool:
        return self.write_u_int(value, 4)

    def write_int_32(self, value: int) -> bool:
        return self.write_int(value, 4)

    def write_u_int_64(self, value: int) -> bool:
        return self.write_to_buffer(struct.pack("<Q", value))

    def write_int_64(self, value: int) -> bool:
        return self.write_to_buffer(struct.pack("<q", value))

    def write_float(self, value: float) -> bool:
        return self.write_to_buffer(struct.pack("<f", value))

    def write_double(self, value: float) -> bool:
        return self.write_to_buffer(struct.pack("<d", value))

    def write_string(self, value: str) -> bool:
        return self.write_to_buffer(value.encode(errors="ignore"))

    def write_bool(self, value: bool) -> bool:
        return self.write_byte(1 if value else 0)

    def write_variant(self, value: int) -> bool:
        arr = []
        length = 0
        while value > 0:
            arr.append(value & 0x7F)
            value >>= 7
            if value != 0:
                arr[length] |= 0x80
            length += 1

        return self.write_to_buffer(bytearray(arr))

    def write_osu_string(self, value: str) -> bool:
        if len(value) == 0:
            self.write_byte(11)
            self.write_byte(0)
        else:
            self.write_byte(11)
            self.write_variant(len(value.encode(errors="ignore")))
            self.write_string(value)

        return True

    def write_u_leb_128(self, value: int) -> bool:
        return self.write_variant(value)

    def write_i32_list(self, list_integers: Tuple[int, ...]) -> bool:
        self.write_u_int_16(len(list_integers))
        for integer in list_integers:
            self.write_u_int_32(integer)

        return True

    def write_mp_match(self, arguments: List[Union["Match", bool]]) -> bool:
        match: "Match" = arguments[0]
        send_pw: bool = arguments[1]

        self.write_int_16(match.id)
        self.write_bool(match.in_progress)
        self.write_byte(match.match_type.value)
        self.write_int_32(match.mods.value)
        self.write_osu_string(match.name)
        if match.password:
            if send_pw:
                self.write_osu_string(match.password)
            else:
                self.write_osu_string(" ")
        else:
            self.write_to_buffer(b"\x00")
        self.write_osu_string(match.beatmap_name)
        self.write_int_32(match.beatmap_id)
        self.write_osu_string(match.beatmap_md5)

        for slot in match.slots:  # add slot status
            self.write_byte(slot.status.value)

        for slot in match.slots:  # add slot team color
            self.write_byte(slot.team.value)

        for slot in match.slots:
            if (
                slot.status.value & SlotStatus.HasPlayer
            ):  # if player exists in that slot, add it
                self.write_int_32(slot.token.id)

        if match.is_tourney:
            if match.host_tourney:
                self.write_int_32(match.host_tourney.id)
            else:
                self.write_int_32(-1)
        else:
            self.write_int_32(match.host.id)

        self.write_byte(match.match_playmode.value)
        self.write_byte(match.match_scoring_type.value)
        self.write_byte(match.match_team_type.value)
        self.write_byte(match.match_freemod.value)

        if match.is_freemod:
            for slot in match.slots:
                self.write_int_32(slot.mods.value)

        self.write_int_32(match.seed)
        return True

    # 1 - packet id
    # 2 - (data, osuType)
    @staticmethod
    def CreateBanchoPacket(
        pid: Union[int, OsuPacketID], *args: Union[Tuple[Any, int]]
    ) -> bytes:
        # writing packet
        writer = KurisoPacketWriter()
        packet_header = struct.pack("<Hx", pid.value if isinstance(pid, OsuPacketID) else pid)

        ptypes = {
            osuTypes.i32_list: writer.write_i32_list,
            osuTypes.string: writer.write_osu_string,
            osuTypes.raw: writer.write_to_buffer,
            osuTypes.match: writer.write_mp_match,
            # TODO: add another custom bancho types
            osuTypes.byte: writer.write_byte,
            osuTypes.bool: writer.write_bool,
            osuTypes.int8: writer.write_int_8,
            osuTypes.u_int8: writer.write_u_int_8,
            osuTypes.int16: writer.write_int_16,
            osuTypes.u_int16: writer.write_u_int_16,
            osuTypes.int32: writer.write_int_32,
            osuTypes.u_int32: writer.write_u_int_32,
            # doesn't care
            osuTypes.float32: writer.write_float,
            osuTypes.float64: writer.write_float,
            osuTypes.int64: writer.write_int_64,
            osuTypes.u_int64: writer.write_u_int_64,
        }

        for packet, packet_type in args:
            if not (p_writer := ptypes.get(packet_type, None)):
                continue  # can't identify packet type

            p_writer(packet)

        packets = writer.get_string()
        return (
            packet_header + len(packets).to_bytes(4, signed=True, byteorder="little") + packets
        )


class PacketBuilder:

    # server packet: 5
    @staticmethod
    def UserID(user_id: int) -> bytes:
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
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_LoginReply.value, (user_id, osuTypes.int32)
        )

    @staticmethod
    def MainMenuIcon(icon: str) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_TitleUpdate.value, (icon, osuTypes.string)
        )

    # server packet: 25
    @staticmethod
    def Notification(message: str) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_Announce, (message, osuTypes.string)
        )

    # server packet: 75
    @staticmethod
    def ProtocolVersion(version: int) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_ProtocolNegotiation.value,
            (version, osuTypes.int32),
        )

    # server packet: 71
    @staticmethod
    def BanchoPrivileges(privs: int) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_LoginPermissions.value, (privs, osuTypes.int32)
        )

    # server packet: 72
    @staticmethod
    def FriendList(friend_list: Union[List[int]]) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_FriendsList.value,
            (friend_list, osuTypes.i32_list),
        )

    # server packet: 92
    @staticmethod
    def SilenceEnd(silence_time: int) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_BanInfo.value, (silence_time, osuTypes.u_int32)
        )

    # server packet: 83
    @staticmethod
    def UserPresence(player: "Player") -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_UserPresence.value,
            (player.id, osuTypes.int32),
            (player.name, osuTypes.string),
            (player.timezone, osuTypes.u_int8),
            (player.country[0], osuTypes.u_int8),
            (player.bancho_privs.value, osuTypes.u_int8),
            (player.location[1], osuTypes.float64),
            (player.location[0], osuTypes.float64),
            (player.current_stats.leaderboard_rank, osuTypes.int32),
        )

    # client packet: 3, bancho response: 11
    @staticmethod
    def UserStats(player: "Player") -> bytes:
        if player.is_tourneymode:
            return b""  # return empty data to hide stats

        return KurisoPacketWriter.CreateBanchoPacket(
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
            (player.current_stats.pp, osuTypes.int16),
        )

    # client packet: 2, bancho response: 12
    @staticmethod
    def Logout(uid: int) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_HandleUserQuit.value,
            (uid, osuTypes.int32),
            (0, osuTypes.u_int8),
        )

    # bancho response: 64
    @staticmethod
    def SuccessJoinChannel(name: str) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_ChannelJoinSuccess.value, (name, osuTypes.string)
        )

    @staticmethod
    def ErrorJoinChannel(name: str) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_ChannelJoinSuccess.value, (name, osuTypes.string)
        )

    # bancho response: 66
    @staticmethod
    def PartChannel(name: str) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_ChannelRevoked.value, (name, osuTypes.string)
        )

    # bancho response: 7
    @staticmethod
    def BuildMessage(uid: int, message: "Message") -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_SendMessage.value,
            (message.sender, osuTypes.string),
            (message.body, osuTypes.string),
            (message.to, osuTypes.string),
            (uid, osuTypes.int32),
        )

    # bancho response: 65
    @staticmethod
    def ChannelAvailable(channel) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_ChannelAvailable.value,
            (channel.name, osuTypes.string),
            (channel.description, osuTypes.string),
            (len(channel.users), osuTypes.int16),
        )

    # bancho response: 89
    @staticmethod
    def ChannelListeningEnd() -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_ChannelListingComplete.value
        )

    # bancho response: 100
    @staticmethod
    def PMBlocked(target: str) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_UserPMBlocked.value,
            ("", osuTypes.string),
            ("", osuTypes.string),
            (target, osuTypes.string),
            (0, osuTypes.int32),
        )

    # bancho response: 101
    @staticmethod
    def TargetSilenced(target: str) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_TargetIsSilenced.value,
            ("", osuTypes.string),
            ("", osuTypes.string),
            (target, osuTypes.string),
            (0, osuTypes.int32),
        )

    # bancho response: 42
    @staticmethod
    def FellowSpectatorJoined(uid: int) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_FellowSpectatorJoined.value,
            (uid, osuTypes.int32),
        )

    # bancho response: 13
    @staticmethod
    def SpectatorJoined(uid: int) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_SpectatorJoined.value, (uid, osuTypes.int32)
        )

    # bancho response: 43
    @staticmethod
    def FellowSpectatorLeft(uid: int) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_FellowSpectatorLeft.value, (uid, osuTypes.int32)
        )

    # bancho response: 14
    @staticmethod
    def SpectatorLeft(uid: int) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_SpectatorLeft.value, (uid, osuTypes.int32)
        )

    # bancho response: 22
    @staticmethod
    def CantSpectate(uid: int) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_SpectatorCantSpectate.value,
            (uid, osuTypes.int32),
        )

    # bancho response: 15
    @staticmethod
    def QuickSpectatorFrame(data: bytes) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_SpectateFrames.value, (data, osuTypes.raw)
        )

    # bancho response: 26
    @staticmethod
    def UpdateMatch(match: "Match", send_pw: bool = True) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_MatchUpdate.value,
            ((match, send_pw), osuTypes.match),
        )

    # bancho response: 27
    @staticmethod
    def NewMatch(match: "Match") -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_MatchNew.value, ((match, False), osuTypes.match)
        )

    # bancho response: 36
    @staticmethod
    def MatchJoinSuccess(match: "Match") -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_MatchJoinSuccess.value,
            ((match, True), osuTypes.match),
        )

    # bancho response: 37
    @staticmethod
    def MatchJoinFailed() -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(OsuPacketID.Bancho_MatchJoinFail.value)

    # bancho response: 46
    @staticmethod
    def InitiateStartMatch(match: "Match") -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_MatchStart.value, ((match, True), osuTypes.match)
        )

    # bancho response: 28
    @staticmethod
    def DisbandMatch(match: "Match") -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_MatchDisband.value, (match.id, osuTypes.int32)
        )

    # bancho response: 50
    @staticmethod
    def MatchHostTransfer() -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(OsuPacketID.Bancho_MatchTransferHost.value)

    # bancho response: 61
    @staticmethod
    def MultiSkip():
        return KurisoPacketWriter.CreateBanchoPacket(OsuPacketID.Bancho_MatchSkip.value)

    # bancho response: 53
    @staticmethod
    def AllPlayersLoaded():
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_MatchAllPlayersLoaded.value
        )

    # bancho response: 48
    @staticmethod
    def MultiScoreUpdate(packet_data: bytearray) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_MatchScoreUpdate.value,
            (packet_data, osuTypes.raw),
        )

    # bancho response: 58
    @staticmethod
    def MatchFinished() -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(OsuPacketID.Bancho_MatchComplete.value)

    # bancho response: 57
    @staticmethod
    def MatchPlayerFailed(slot_ind: int) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_MatchPlayerFailed.value,
            (slot_ind, osuTypes.int16),
        )

    # bancho response: 86
    @staticmethod
    def BanchoRestarting(ms: int) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_Restart, (ms, osuTypes.u_int32)
        )

    # bancho response: 94
    @staticmethod
    def UserSilenced(user_id: int) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_UserSilenced.value, (user_id, osuTypes.u_int32)
        )

    # bancho response: 104
    @staticmethod
    def UserRestricted() -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(OsuPacketID.Bancho_AccountRestricted.value)

    # bancho response: 107
    @staticmethod
    def SwitchServer(new_server: str) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_SwitchTourneyServer.value,
            (new_server, osuTypes.string),
        )

    # bancho response: 105
    @staticmethod
    def RTX(message: str) -> bytes:
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_RTX.value, (message, osuTypes.string)
        )

    # bancho response: 0 but with bad byte
    @staticmethod
    def KillPing():
        return KurisoPacketWriter.CreateBanchoPacket(
            OsuPacketID.Bancho_Ping.value, (0, osuTypes.byte)
        )

    # bancho response: 106
    @staticmethod
    def MatchAborted():
        return KurisoPacketWriter.CreateBanchoPacket(OsuPacketID.Client_MatchAbort.value)
