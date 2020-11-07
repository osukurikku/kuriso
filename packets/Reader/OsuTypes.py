from enum import IntEnum, unique

__all__ = 'osuTypes',
__author__ = "cmyui"


@unique
class osuTypes(IntEnum):
    # integral
    int8 = 0
    u_int8 = 1
    int16 = 2
    u_int16 = 3
    int32 = 4
    u_int32 = 5
    float32 = 6
    int64 = 7
    u_int64 = 8
    float64 = 9

    # osu
    message = 11
    channel = 12
    match = 13
    score_frame = 14
    map_info_request = 15
    map_info_reply = 16

    # misc
    i32_list = 17 # 2 bytes len
    i32_list4l = 18 # 4 bytes len
    string = 19
    raw = 20