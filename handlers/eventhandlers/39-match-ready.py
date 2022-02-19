from bot.bot import CrystalBot
from handlers.decorators import OsuEvent
from objects.constants.Slots import SlotStatus
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 39, bancho response: update match
@OsuEvent.register_handler(OsuPacketID.Client_MatchReady)
async def match_ready(_, token: "Player"):
    if not token.match:
        return False

    match = token.match
    currentSlot = match.get_slot(token)
    currentSlot.status = SlotStatus.Ready

    if match.is_tourney and all(
        slot.status == SlotStatus.Ready
        for slot in match.slots_with_status(SlotStatus.HasPlayer)
    ):
        await CrystalBot.ez_message(f"#multi_{match.id}", "All players are ready!")

    await match.update_match()
    return True
