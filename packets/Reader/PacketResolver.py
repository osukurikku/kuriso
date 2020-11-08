from typing import List

from packets.Reader.index import KorchoBuffer


class PacketResolver:

    @staticmethod
    async def read_new_presence(data: bytes) -> dict:
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
