import io
import struct  # for unpacking/packing float, double
from typing import Union, Tuple, List, Any, Optional

from objects.constants.Slots import SlotStatus
from packets.OsuPacketID import OsuPacketID
from packets.Reader.OsuTypes import osuTypes as OsuTypes

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from objects.Multiplayer import Match


class KorchoBuffer:
    """
    Very important class ported from JS osu-buffer by @KotRikD
    """
    __slots__ = ("buffer", "position")

    def __init__(self, input_str: Optional[str]):
        if input_str:
            self.buffer = io.BytesIO(input_str.encode(encoding="utf-8"))
        else:
            self.buffer = io.BytesIO(b"")
        self.position = 0

    @property
    def length(self) -> int:
        return self.buffer.getbuffer().nbytes

    def get_string(self) -> bytes:
        return self.buffer.getvalue()

    async def can_read(self, length: int) -> bool:
        return length + self.position <= self.length

    def EOF(self) -> bool:
        return self.position >= self.length

    async def slice_buffer(self, length: int) -> bytes:
        self.position += length
        return bytes(self.buffer.getbuffer()[slice(self.position - length, self.position)])

    async def peek(self) -> bytes:
        return bytes(self.buffer.getbuffer()[self.position + 1])

    async def read_int(self, byte_length: int) -> int:
        self.position += byte_length
        return int.from_bytes(bytes(self.buffer.getbuffer()[slice(self.position - byte_length, self.position)]),
                              byteorder='little',
                              signed=True)

    async def read_u_int(self, byte_length: int) -> int:
        self.position += byte_length
        return int.from_bytes(bytes(self.buffer.getbuffer()[slice(self.position - byte_length, self.position)]),
                              byteorder='little',
                              signed=False)

    async def read_float(self) -> float:
        self.position += 4  # float size = 4
        return struct.unpack("<f", bytes(self.buffer.getbuffer()[slice(self.position - 4, self.position)]))[0]

    async def read_double(self) -> float:
        self.position += 8  # double size = 8
        return struct.unpack("<d", bytes(self.buffer.getbuffer()[slice(self.position - 8, self.position)]))[0]

    async def read_string(self, length) -> str:
        return (await self.slice_buffer(length)).decode("latin_1", errors="ignore")  # ignore, because meh

    async def read_int_8(self) -> int:
        return await self.read_int(1)

    async def read_u_int_8(self) -> int:
        return await self.read_u_int(1)

    async def read_int_16(self) -> int:
        return await self.read_int(2)

    async def read_u_int_16(self) -> int:
        return await self.read_u_int(2)

    async def read_int_32(self) -> int:
        return await self.read_int(4)

    async def read_u_int_32(self) -> int:
        return await self.read_u_int(4)

    async def read_int_64(self) -> int:
        return (await self.read_int(4) << 8) + await self.read_int(4)

    async def read_u_int_64(self) -> int:
        return (await self.read_u_int(4) << 8) + await self.read_u_int(4)

    async def read_variant(self) -> int:  # big function af, which i doesn't know how to work
        total = 0
        shift = 0
        byte = await self.read_u_int_8()
        if (byte & 0x80) == 0:
            total |= ((byte & 0x7F) << shift)
        else:
            end = False
            while not end:
                if shift:
                    byte = await self.read_u_int_8()
                total |= ((byte & 0x7F) << shift)
                if (byte & 0x80) == 0:
                    end = True
                shift += 7

        return total

    async def read_u_leb_128(self) -> int:
        return await self.read_variant()

    async def read_bool(self) -> bool:
        return bool(await self.read_int(1))

    async def read_byte(self) -> int:
        return await self.read_u_int_8()

    async def read_osu_string(self) -> str:
        is_string = (await self.read_byte()) == 11
        if is_string:
            length = await self.read_variant()
            return await self.read_string(length)

        return ''

    async def read_i32_list(self) -> List[int]:
        length = await self.read_u_int_16()
        integers = []
        for _ in range(length):
            integers.append(await self.read_u_int_32())

        return integers

    async def write_to_buffer(self, value: Union[bytes, bytearray]):
        self.buffer.write(value)
        return True

    async def write_u_int(self, value: int, byte_length: int) -> bool:
        self.buffer.write(value.to_bytes(byte_length, byteorder='little', signed=False))
        return True

    async def write_int(self, value: int, byte_length: int) -> bool:
        self.buffer.write(value.to_bytes(byte_length, byteorder='little', signed=True))
        return True

    async def write_byte(self, value: int) -> bool:
        return await self.write_u_int(value, 1)

    async def write_bytes(self, value: Union[Tuple, List]):
        return await self.write_to_buffer(bytearray(value))

    async def write_u_int_8(self, value: int) -> bool:
        return await self.write_u_int(value, 1)

    async def write_int_8(self, value: int) -> bool:
        return await self.write_int(value, 1)

    async def write_u_int_16(self, value: int) -> bool:
        return await self.write_u_int(value, 2)

    async def write_int_16(self, value: int) -> bool:
        return await self.write_int(value, 2)

    async def write_u_int_32(self, value: int) -> bool:
        return await self.write_u_int(value, 4)

    async def write_int_32(self, value: int) -> bool:
        return await self.write_int(value, 4)

    async def write_u_int_64(self, value: int) -> bool:
        return await self.write_to_buffer(struct.pack("<Q", value))

    async def write_int_64(self, value: int) -> bool:
        return await self.write_to_buffer(struct.pack("<q", value))

    async def write_float(self, value: float) -> bool:
        return await self.write_to_buffer(struct.pack("<f", value))

    async def write_double(self, value: float) -> bool:
        return await self.write_to_buffer(struct.pack("<d", value))

    async def write_string(self, value: str) -> bool:
        return await self.write_to_buffer(value.encode("latin_1", errors="ignore"))

    async def write_bool(self, value: bool) -> bool:
        return await self.write_byte(1 if value else 0)

    async def write_variant(self, value: int) -> bool:
        arr = []
        length = 0
        while value > 0:
            arr.append(value & 0x7F)
            value >>= 7
            if value != 0:
                arr[length] |= 0x80
            length += 1

        return await self.write_to_buffer(bytearray(arr))

    async def write_osu_string(self, value: str) -> bool:
        if len(value) == 0:
            await self.write_byte(11)
            await self.write_byte(0)
        else:
            await self.write_byte(11)
            await self.write_variant(len(value))
            await self.write_string(value)

        return True

    async def write_u_leb_128(self, value: int) -> bool:
        return await self.write_variant(value)

    async def write_i32_list(self, list_integers: Tuple[int, ...]) -> bool:
        await self.write_u_int_16(len(list_integers))
        for integer in list_integers:
            await self.write_u_int_32(integer)

        return True

    async def write_mp_match(self, arguments: List[Union['Match', bool]]) -> bool:
        match: 'Match' = arguments[0]
        send_pw: bool = arguments[1]

        await self.write_int_16(match.id)
        await self.write_bool(match.in_progress)
        await self.write_byte(match.match_type.value)
        await self.write_int_32(match.mods.value)
        await self.write_osu_string(match.name)
        if match.password:
            if send_pw:
                await self.write_osu_string(match.password)
            else:
                await self.write_osu_string(" ")
        else:
            await self.write_to_buffer(b"\x00")
        await self.write_osu_string(match.beatmap_name)
        await self.write_int_32(match.beatmap_id)
        await self.write_osu_string(match.beatmap_md5)

        for slot in match.slots:  # add slot status
            await self.write_byte(slot.status.value)

        for slot in match.slots:  # add slot team color
            await self.write_byte(slot.team.value)

        for slot in match.slots:
            if (slot.status.value & SlotStatus.HasPlayer.value) > 0:  # if player exists in that slot, add it
                await self.write_int_32(slot.token.id)

        await self.write_int_32(match.host.id)  # match -> token (host) -> id
        await self.write_byte(match.match_playmode.value)
        await self.write_byte(match.match_scoring_type.value)
        await self.write_byte(match.match_team_type.value)
        await self.write_byte(match.match_freemod.value)

        if match.is_freemod:
            for slot in match.slots:
                await self.write_int_32(slot.mods.value)

        await self.write_int_32(match.seed)
        return True


# 1 - packet id
# 2 - (data, osuType)
async def CreateBanchoPacket(pid: Union[int, OsuPacketID], *args: Union[Tuple[Any, int]]) -> bytes:
    # writing packet
    dataBuffer = KorchoBuffer(None)
    packet_header = struct.pack("<Hx", pid.value if isinstance(pid, OsuPacketID) else pid)

    ptypes = {
        OsuTypes.i32_list: dataBuffer.write_i32_list,
        OsuTypes.string: dataBuffer.write_osu_string,
        OsuTypes.raw: dataBuffer.write_to_buffer,
        OsuTypes.match: dataBuffer.write_mp_match,
        # TODO: add another custom bancho types

        OsuTypes.byte: dataBuffer.write_byte,
        OsuTypes.bool: dataBuffer.write_bool,
        OsuTypes.int8: dataBuffer.write_int_8,
        OsuTypes.u_int8: dataBuffer.write_u_int_8,
        OsuTypes.int16: dataBuffer.write_int_16,
        OsuTypes.u_int16: dataBuffer.write_u_int_16,
        OsuTypes.int32: dataBuffer.write_int_32,
        OsuTypes.u_int32: dataBuffer.write_u_int_32,
        # doesn't care
        OsuTypes.float32: dataBuffer.write_float,
        OsuTypes.float64: dataBuffer.write_float,
        OsuTypes.int64: dataBuffer.write_int_64,
        OsuTypes.u_int64: dataBuffer.write_u_int_64
    }

    for packet, packet_type in args:
        writer = ptypes.get(packet_type, None)
        if not writer:
            continue  # can't identify packet type

        await writer(packet)

    packetArray = packet_header + dataBuffer.length.to_bytes(4, signed=True, byteorder="little") + dataBuffer.get_string()
    return packetArray
