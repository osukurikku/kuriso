import time

from handlers.decorators import OsuEvent
from lib import logger
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 2,
@OsuEvent.register_handler(OsuPacketID.Client_Exit)
async def logout(_, token: "Player"):
    if (time.time() - token.login_time) < 5:
        # weird osu scheme that all already knows
        return

    await token.logout()
    logger.klog(f"[{token.name}] Leaved kuriso!")
    return True
