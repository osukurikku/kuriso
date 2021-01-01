from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID


# packet id: 29 leave lobby
@OsuEvent.register_handler(OsuPacketID.Client_LobbyPart)
async def refresh_user_stats(*_):
    return True
