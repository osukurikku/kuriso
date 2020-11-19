from typing import Union

from packets.OsuPacketID import OsuPacketID


class OsuEvent:

    handlers = {}

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(OsuEvent, cls).__new__(cls)
        return cls.instance

    @classmethod
    def register_handler(cls, packet_id: Union[int, OsuPacketID]):
        def wrapper(func):
            cls.handlers[packet_id.value if isinstance(packet_id, OsuPacketID) else packet_id] = func

        return wrapper
