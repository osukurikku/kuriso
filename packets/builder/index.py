import objects.Token
from packets.OsuPacketID import OsuPacketID
from packets.Reader.OsuTypes import osuTypes
from packets.Reader.index import CreateBanchoPacket


class PacketBuilder:

    # client packet: 3, bancho response: 11
    @staticmethod
    async def RefreshUserStats(player: objects.Token.Token) -> bytes:
        return await CreateBanchoPacket(OsuPacketID.Bancho_HandleOsuUpdate,
                                        (1000, osuTypes.int32),  # userID
                                        (0, osuTypes.u_int8),  # status
                                        ("flexing on kuriso", osuTypes.string),  # title
                                        ("", osuTypes.string),  # beatmap-md5
                                        (0, osuTypes.int32),  # mods
                                        (0, osuTypes.u_int8),  # playmode
                                        (0, osuTypes.int32),  # beatmap id
                                        (1, osuTypes.int64),  # ranked score
                                        (1, osuTypes.float32),  # accuracy in probability
                                        (1, osuTypes.int32),  # total plays
                                        (1, osuTypes.int64),  # total score
                                        (1, osuTypes.int32),  # playmode rank
                                        (1, osuTypes.int16)  # pp
                                        )

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

    # server packet: 25
    @staticmethod
    async def Notification(message: str) -> bytes:
        return await CreateBanchoPacket(
            OsuPacketID.Bancho_Announce,
            (message, osuTypes.string)
        )
