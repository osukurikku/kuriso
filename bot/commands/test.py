from typing import List, TYPE_CHECKING
from bot.bot import CrystalBot

if TYPE_CHECKING:
    from objects.Player import Player


@CrystalBot.register_command("!test")
async def test_command(args: List[str], player: 'Player'):
    return f'Complete! Echo: {" ".join(args)}. Hi! {player.name}'
