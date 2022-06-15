from typing import List, Tuple

from objects.TypedDicts import TypedPresence, TypedReadMatch
from objects.constants.GameModes import GameModes
from objects.constants.Modificators import Mods
from objects.constants.Slots import SlotStatus, SlotTeams
from objects.constants.multiplayer import (
    MatchTypes,
    MatchScoringTypes,
    MatchTeamTypes,
    MultiSpecialModes,
)
from objects.Multiplayer import Slot

from objects.BanchoObjects import Message
from packets.Reader.index import KurisoPacketReader


class PacketResolver:
    @staticmethod
    def read_new_presence(data: bytes) -> TypedPresence:
        with memoryview(data) as buffer:
            reader = KurisoPacketReader(buffer)
            return {
                "action": reader.read_byte(),
                "action_text": reader.read_osu_string(),
                "map_md5": reader.read_osu_string(),
                "mods": reader.read_u_int_32(),
                "mode": reader.read_byte(),
                "map_id": reader.read_int_32(),
            }

    @staticmethod
    def read_request_users_stats(data: bytes) -> List[int]:
        with memoryview(data) as buffer:
            reader = KurisoPacketReader(buffer)
            return reader.read_i32_list()

    @staticmethod
    def read_pr_filter(data: bytes) -> int:
        with memoryview(data) as buffer:
            reader = KurisoPacketReader(buffer)
            return reader.read_int_32()

    @staticmethod
    def read_slot_index(data: bytes) -> int:
        with memoryview(data) as buffer:
            reader = KurisoPacketReader(buffer)
            return reader.read_int_32()

    @staticmethod
    def read_message(data: bytes) -> Message:
        with memoryview(data) as buffer:
            reader = KurisoPacketReader(buffer)
            return Message(
                sender=reader.read_osu_string(),
                body=reader.read_osu_string(),
                to=reader.read_osu_string(),
                client_id=reader.read_int_32(),
            )

    @staticmethod
    def read_channel_name(data: bytes) -> str:
        with memoryview(data) as buffer:
            reader = KurisoPacketReader(buffer)
            return reader.read_osu_string()

    @staticmethod
    def read_specatator_id(data: bytes) -> int:
        with memoryview(data) as buffer:
            reader = KurisoPacketReader(buffer)
            return reader.read_int_32()

    @staticmethod
    def read_friend_id(data: bytes) -> int:
        with memoryview(data) as buffer:
            reader = KurisoPacketReader(buffer)
            return reader.read_int_32()

    @staticmethod
    def read_match(data: bytes) -> TypedReadMatch:
        with memoryview(data) as buffer:
            reader = KurisoPacketReader(buffer)

            reader.read_int_16()  # skip 3 bytes for id and inProgress because default is False
            reader.read_byte()

            match_type = MatchTypes(reader.read_byte())
            mods = Mods(reader.read_int_32())

            name = reader.read_osu_string()
            password = reader.read_osu_string()

            beatmap_name = reader.read_osu_string()
            beatmap_id = reader.read_int_32()
            beatmap_md5 = reader.read_osu_string()

            slots = [Slot() for _ in range(0, 16)]  # make slots
            for slot in slots:
                slot.status = SlotStatus(reader.read_byte())

            for slot in slots:
                slot.team = SlotTeams(reader.read_byte())

            for slot in slots:
                if slot.status.value & SlotStatus.HasPlayer:
                    reader.read_int_32()

            host_id = reader.read_int_32()
            play_mode = GameModes(reader.read_byte())
            scoring_type = MatchScoringTypes(reader.read_byte())
            team_type = MatchTeamTypes(reader.read_byte())
            is_freemod = reader.read_bool()
            match_freemod = MultiSpecialModes(int(is_freemod))

            if is_freemod:
                for slot in slots:
                    slot.mods = Mods(reader.read_int_32())

            seed = reader.read_int_32()

            t_dict = {
                "match_type": match_type,
                "mods": mods,
                "name": name,
                "password": password,
                "beatmap_name": beatmap_name,
                "beatmap_id": beatmap_id,
                "beatmap_md5": beatmap_md5,
                "slots": slots,
                "host_id": host_id,
                "play_mode": play_mode,
                "scoring_type": scoring_type,
                "team_type": team_type,
                "match_freemod": match_freemod,
                "seed": seed,
            }

            return t_dict

    @staticmethod
    def read_mp_join_data(data: bytes) -> Tuple[int, str]:
        with memoryview(data) as buffer:
            reader = KurisoPacketReader(buffer)
            return reader.read_int_32(), reader.read_osu_string()

    @staticmethod
    def read_mods(data: bytes) -> int:
        with memoryview(data) as buffer:
            reader = KurisoPacketReader(buffer)
            return reader.read_int_32()

    @staticmethod
    def read_user_id(data: bytes) -> int:
        with memoryview(data) as buffer:
            reader = KurisoPacketReader(buffer)
            return reader.read_int_32()

    @staticmethod
    def read_match_id(data: bytes) -> int:
        with memoryview(data) as buffer:
            reader = KurisoPacketReader(buffer)
            return reader.read_int_32()
