import queue
from typing import Union, Optional, Dict, Tuple, TYPE_CHECKING

from blob import Context
from helpers import userHelper
from objects.Player import Player

if TYPE_CHECKING:
    from objects.Multiplayer import Match


class TourneyPlayer(Player):
    """
    THAT IS NOT GOOD REALIZATION OF TOURNEY CONNECTION
    BUT I HADN'T GOOD IDEA HOW?!
    BECAUSE WITH THAT IMPLEMENTATION
    POSSIBLE VARIANTS:

    manager: [additional_osu_windows]

    AND VARIANT THAT I CAN'T EXCEPT

    additional_osu_window_<any>: [manager, other_additional_osu_windows] <- if that case, i even don't know what can happened

    BUT IT WAS CHECKED AND LGTM, THAT WHY THIS EXIST
    """

    def __init__(self, user_id: Union[int], user_name: Union[str], privileges: Union[int],
                 utc_offset: Optional[int] = 0, pm_private: bool = False, silence_end: int = 0,
                 is_tourneymode: bool = False, ip: str = ''):
        super().__init__(user_id, user_name, privileges, utc_offset, pm_private, silence_end, is_tourneymode, False, ip)

        self.additional_clients: Dict[str, 'Player'] = {}

    def add_additional_client(self) -> Tuple[str, 'Player']:
        token = self.generate_token()
        self.additional_clients[token] = Player(self.id, self.name, self.privileges, self.timezone_offset,
                                                self.pm_private, self.silence_end, self.is_tourneymode,
                                                self.is_bot, self.ip)
        self.additional_clients[token].token = token
        self.additional_clients[token].stats = self.stats
        return token, self.additional_clients[token]

    def remove_additional_client(self, token: str) -> bool:
        if token in self.additional_clients:
            self.additional_clients.pop(token)

        return True

    @property
    def match(self) -> 'Match':
        return None if self.id_tourney < 0 else Context.matches.get(self.id_tourney, None)

    async def logout(self) -> None:
        if self.ip:
            await userHelper.deleteBanchoSession(self.id, self.ip)

        await super().logout()  # super() will ignore ^ delete bancho session
        return
