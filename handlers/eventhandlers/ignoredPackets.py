from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID


# packet id: 68 beatmap info request, not used in newer client
@OsuEvent.register_handler(OsuPacketID.Client_BeatmapInfoRequest)
async def _(*_):
    return True
