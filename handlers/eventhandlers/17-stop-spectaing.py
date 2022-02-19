from lib import logger
from handlers.decorators import OsuEvent
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 17, bancho response: 43
@OsuEvent.register_handler(OsuPacketID.Client_StopSpectating)
async def leave_spectator(_, token: "Player"):
    old_victim = token.spectating

    if not old_victim:
        logger.elog(f"{token.name} tried to stop spectating empty old victim...")
        return False  # because this is bug and impossible in context

    if token.is_tourneymode:
        await old_victim.remove_hidden_spectator(token)
    else:
        await old_victim.remove_spectator(token)
    return True
