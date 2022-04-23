import struct  # for unpacking/packing float, double
from typing import List


class KurisoPacketReader:
    """
    Very important class ported from JS osu-buffer by @KotRikD
    """

    __slots__ = ("buffer", "position")

    def __init__(self, buffer: memoryview):
        self.buffer = buffer
        self.position = 0

    @property
    def length(self) -> int:
        return self.buffer.nbytes

    def get_string(self) -> bytes:
        return self.buffer.tobytes()

    def can_read(self, length: int) -> bool:
        return length + self.position <= self.length

    def EOF(self) -> bool:
        return self.position >= self.length

    def slice_buffer(self, length: int) -> bytes:
        self.position += length
        return bytes(self.buffer[slice(self.position - length, self.position)])

    def peek(self) -> bytes:
        return bytes(self.buffer[self.position + 1])

    def read_int(self, byte_length: int) -> int:
        self.position += byte_length
        return int.from_bytes(
            bytes(self.buffer[slice(self.position - byte_length, self.position)]),
            byteorder="little",
            signed=True,
        )

    def read_u_int(self, byte_length: int) -> int:
        self.position += byte_length
        return int.from_bytes(
            bytes(self.buffer[slice(self.position - byte_length, self.position)]),
            byteorder="little",
            signed=False,
        )

    def read_float(self) -> float:
        self.position += 4  # float size = 4
        return struct.unpack(
            "<f",
            bytes(self.buffer[slice(self.position - 4, self.position)]),
        )[0]

    def read_double(self) -> float:
        self.position += 8  # double size = 8
        return struct.unpack(
            "<d",
            bytes(self.buffer[slice(self.position - 8, self.position)]),
        )[0]

    def read_int_8(self) -> int:
        return self.read_int(1)

    def read_string(self, length) -> str:
        return (self.slice_buffer(length)).decode(errors="ignore")  # ignore, because meh

    def read_u_int_8(self) -> int:
        return self.read_u_int(1)

    def read_int_16(self) -> int:
        return self.read_int(2)

    def read_u_int_16(self) -> int:
        return self.read_u_int(2)

    def read_int_32(self) -> int:
        return self.read_int(4)

    def read_u_int_32(self) -> int:
        return self.read_u_int(4)

    def read_int_64(self) -> int:
        return (self.read_int(4) << 8) + self.read_int(4)

    def read_u_int_64(self) -> int:
        return (self.read_u_int(4) << 8) + self.read_u_int(4)

    def read_variant(
        self,
    ) -> int:  # big function af, which i doesn't know how to work
        total = 0
        shift = 0
        byte = self.read_u_int_8()
        if (byte & 0x80) == 0:
            total |= (byte & 0x7F) << shift
        else:
            end = False
            while not end:
                if shift:
                    byte = self.read_u_int_8()
                total |= (byte & 0x7F) << shift
                if (byte & 0x80) == 0:
                    end = True
                shift += 7

        return total

    def read_u_leb_128(self) -> int:
        return self.read_variant()

    def read_bool(self) -> bool:
        return bool(self.read_int(1))

    def read_byte(self) -> int:
        return self.read_u_int_8()

    def read_osu_string(self) -> str:
        is_string = (self.read_byte()) == 11
        if is_string:
            length = self.read_variant()
            return self.read_string(length)

        return ""

    def read_i32_list(self) -> List[int]:
        length = self.read_u_int_16()
        integers = []
        for _ in range(length):
            integers.append(self.read_u_int_32())

        return integers
