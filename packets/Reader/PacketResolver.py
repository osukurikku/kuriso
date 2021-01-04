from typing import List, Tuple

from objects.TypedDicts import TypedPresence, TypedReadMatch
from objects.constants.GameModes import GameModes
from objects.constants.Modificators import Mods
from objects.constants.Slots import SlotStatus, SlotTeams
from objects.constants.multiplayer import MatchTypes, MatchScoringTypes, MatchTeamTypes, MultiSpecialModes
from objects.Multiplayer import Slot

from objects.BanchoObjects import Message
from packets.Reader.index import KorchoBuffer


class PacketResolver:

    @staticmethod
    async def read_new_presence(data: bytes) -> TypedPresence:
        buffer = KorchoBuffer(None)
        await buffer.write_to_buffer(data)
        return {
            'action': await buffer.read_byte(),
            'action_text': await buffer.read_osu_string(),
            'map_md5': await buffer.read_osu_string(),
            'mods': await buffer.read_u_int_32(),
            'mode': await buffer.read_byte(),
            'map_id': await buffer.read_int_32()
        }

    @staticmethod
    async def read_request_users_stats(data: bytes) -> List[int]:
        buffer = KorchoBuffer(None)
        await buffer.write_to_buffer(data)
        return await buffer.read_i32_list()

    @staticmethod
    async def read_pr_filter(data: bytes) -> int:
        buffer = KorchoBuffer(None)
        await buffer.write_to_buffer(data)
        return await buffer.read_int_32()

    @staticmethod
    async def read_slot_index(data: bytes) -> int:
        buffer = KorchoBuffer(None)
        await buffer.write_to_buffer(data)
        return await buffer.read_int_32()

    @staticmethod
    async def read_message(data: bytes) -> Message:
        buffer = KorchoBuffer(None)
        await buffer.write_to_buffer(data)
        return Message(
            sender=await buffer.read_osu_string(),
            body=await buffer.read_osu_string(),
            to=await buffer.read_osu_string(),
            client_id=await buffer.read_int_32()
        )

    @staticmethod
    async def read_channel_name(data: bytes) -> str:
        buffer = KorchoBuffer(None)
        await buffer.write_to_buffer(data)
        return await buffer.read_osu_string()

    @staticmethod
    async def read_specatator_id(data: bytes) -> int:
        buffer = KorchoBuffer(None)
        await buffer.write_to_buffer(data)
        return await buffer.read_int_32()

    @staticmethod
    async def read_friend_id(data: bytes) -> int:
        buffer = KorchoBuffer(None)
        await buffer.write_to_buffer(data)
        return await buffer.read_int_32()

    @staticmethod
    async def read_match(data: bytes) -> TypedReadMatch:
        buffer = KorchoBuffer(None)
        await buffer.write_to_buffer(data)

        await buffer.read_int_16()  # skip 3 bytes for id and inProgress because default is False
        await buffer.read_byte()

        match_type = MatchTypes(await buffer.read_byte())
        mods = Mods(await buffer.read_int_32())

        name = await buffer.read_osu_string()
        password = await buffer.read_osu_string()

        beatmap_name = await buffer.read_osu_string()
        beatmap_id = await buffer.read_int_32()
        beatmap_md5 = await buffer.read_osu_string()

        slots = [Slot() for _ in range(0, 16)]  # make slots
        for slot in slots:
            slot.status = SlotStatus(await buffer.read_byte())

        for slot in slots:
            slot.team = SlotTeams(await buffer.read_byte())

        for slot in slots:
            if slot.status.value & SlotStatus.HasPlayer:
                await buffer.read_int_32()

        host_id = await buffer.read_int_32()
        play_mode = GameModes(await buffer.read_byte())
        scoring_type = MatchScoringTypes(await buffer.read_byte())
        team_type = MatchTeamTypes(await buffer.read_byte())
        is_freemod = await buffer.read_bool()
        match_freemod = MultiSpecialModes(int(is_freemod))

        if is_freemod:
            for slot in slots:
                slot.mods = Mods(await buffer.read_int_32())

        seed = await buffer.read_int_32()

        t_dict = {
            'match_type': match_type,
            'mods': mods,
            'name': name,
            'password': password,
            'beatmap_name': beatmap_name,
            'beatmap_id': beatmap_id,
            'beatmap_md5': beatmap_md5,
            'slots': slots,
            'host_id': host_id,
            'play_mode': play_mode,
            'scoring_type': scoring_type,
            'team_type': team_type,
            'match_freemod': match_freemod,
            'seed': seed
        }

        return t_dict

    @staticmethod
    async def read_mp_join_data(data: bytes) -> Tuple[int, str]:
        buffer = KorchoBuffer(None)
        await buffer.write_to_buffer(data)
        return await buffer.read_int_32(), await buffer.read_osu_string()

    @staticmethod
    async def read_mods(data: bytes) -> int:
        buffer = KorchoBuffer(None)
        await buffer.write_to_buffer(data)
        return await buffer.read_int_32()

    @staticmethod
    async def read_user_id(data: bytes) -> int:
        buffer = KorchoBuffer(None)
        await buffer.write_to_buffer(data)
        return await buffer.read_int_32()

    @staticmethod
    async def read_match_id(data: bytes) -> int:
        buffer = KorchoBuffer(None)
        await buffer.write_to_buffer(data)
        return await buffer.read_int_32()
