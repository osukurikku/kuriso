import queue
from typing import Union, Optional, Dict, Tuple

from objects.Player import Player


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
                 is_tourneymode: bool = False):
        super().__init__(user_id, user_name, privileges, utc_offset, pm_private, silence_end, is_tourneymode)

        self.additional_clients: Dict[str, 'Player'] = {}

    def add_additional_client(self) -> Tuple[str, 'Player']:
        token = self.generate_token()
        self.additional_clients[token] = Player(self.id, self.name, self.privileges, self.timezone_offset,
                                                self.pm_private, self.silence_end, self.is_tourneymode)
        self.additional_clients[token].token = token
        self.additional_clients[token].stats = self.stats
        return token, self.additional_clients[token]

    def remove_additional_client(self, token: str) -> bool:
        if token in self.additional_clients:
            self.additional_clients.pop(token)

        return True

    def enqueue(self, b: bytes) -> None:
        self.queue.put_nowait(b)

    def dequeue(self) -> Optional[bytes]:
        try:
            # to_dequeue: bytes = self.queue.get_nowait()
            # for (_, sub_p) in self.additional_clients.items():
            #     sub_p.enqueue(to_dequeue)

            return self.queue.get_nowait()
        except queue.Empty:
            pass