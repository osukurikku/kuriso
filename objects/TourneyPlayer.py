from typing import Optional, Dict, Tuple, TYPE_CHECKING

from blob import Context
from helpers import userHelper
from objects.Player import Player

if TYPE_CHECKING:
    from objects.Multiplayer import Match
    from objects.BanchoObjects import Message


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

    def __init__(
        self,
        user_id: int,
        user_name: str,
        privileges: int,
        utc_offset: Optional[int] = 0,
        pm_private: bool = False,
        silence_end: int = 0,
        is_tourneymode: bool = False,
        ip: str = "",
    ):
        super().__init__(
            user_id,
            user_name,
            privileges,
            utc_offset,
            pm_private,
            silence_end,
            is_tourneymode,
            False,
            ip,
        )

        self.additional_clients: Dict[str, "Player"] = {}

    def add_additional_client(self, client=None, token=None) -> Tuple[str, "Player"]:
        if client and token:
            self.additional_clients[token] = client
            return token, client

        token = self.generate_token()
        self.additional_clients[token] = Player(
            self.id,
            self.name,
            self.privileges,
            self.timezone_offset,
            self.pm_private,
            self.silence_end,
            self.is_tourneymode,
            self.is_bot,
            self.ip,
        )
        self.additional_clients[token].token = token
        self.additional_clients[token].stats = self.stats
        return token, self.additional_clients[token]

    def remove_additional_client(self, token: str) -> bool:
        if token in self.additional_clients:
            self.additional_clients.pop(token)

        return True

    @property
    def match(self) -> "Match":
        return None if self.id_tourney < 0 else Context.matches.get(self.id_tourney, None)

    async def logout(self) -> None:
        if self.ip:
            await userHelper.deleteBanchoSession(self.id, self.ip)

        await super().logout()  # super() will ignore ^ delete bancho session
        return

    async def on_another_user_logout(self, p: "Player") -> None:
        f_irc = list(filter(lambda u: hasattr(u, "irc"), self.additional_clients.values()))
        for irc in f_irc:
            await irc.on_another_user_logout(p)

        return await super().on_another_user_logout(p)

    async def on_message(self, from_id: int, message: "Message", **kwargs) -> None:
        f_irc = list(filter(lambda u: hasattr(u, "irc"), self.additional_clients.values()))
        for irc in f_irc:
            await irc.on_message(from_id, message, **kwargs)

        return await super().on_message(from_id, message, **kwargs)

    async def on_channel_another_user_join(self, p_name: str, **kwargs) -> None:
        f_irc = list(filter(lambda u: hasattr(u, "irc"), self.additional_clients.values()))
        for irc in f_irc:
            await irc.on_channel_another_user_join(p_name, **kwargs)

        return await super().on_channel_another_user_join(p_name, **kwargs)

    async def on_channel_another_user_leave(self, p_name: str, **kwargs) -> None:
        f_irc = list(filter(lambda u: hasattr(u, "irc"), self.additional_clients.values()))
        for irc in f_irc:
            await irc.on_channel_another_user_leave(p_name, **kwargs)

        return await super().on_channel_another_user_leave(p_name, **kwargs)

    async def on_channel_join(self, channel_name: str, server_name: str) -> None:
        f_irc = list(filter(lambda u: hasattr(u, "irc"), self.additional_clients.values()))
        for irc in f_irc:
            await irc.on_channel_join(channel_name, server_name)

        return await super().on_channel_join(channel_name, server_name)

    async def on_channel_leave(self, channel_name: str, server_name: str) -> None:
        f_irc = list(filter(lambda u: hasattr(u, "irc"), self.additional_clients.values()))
        for irc in f_irc:
            await irc.on_channel_leave(channel_name, server_name)

        return await super().on_channel_leave(channel_name, server_name)
