import time

import objects.Player
from handlers.decorators import OsuEvent
from lib import logger
from packets.OsuPacketID import OsuPacketID


# client packet: 2,
@OsuEvent.register_handler(OsuPacketID.Client_Exit)
async def logout(packet_data: bytes, token: objects.Player.Player):
    if (time.time() - token.login_time) < 5:
        # weird osu scheme that all already knows
        return

    await token.logout()
    logger.klog(f"[{token.name}] Leaved kuriso!")
    return True

