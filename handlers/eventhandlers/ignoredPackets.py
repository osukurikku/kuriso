from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID


# packet id: 29 leave lobby
@OsuEvent.register_handler(OsuPacketID.Client_LobbyPart)
async def _(*_):
    return True


# packet id: 68 beatmap info request, not used in newer client
@OsuEvent.register_handler(OsuPacketID.Client_BeatmapInfoRequest)
async def _(*_):
    return True
