from typing import Union, TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from objects.Player import Player
    from objects.TourneyPlayer import TourneyPlayer


class TokenStorage:
    __slots__ = ('store_by_token', 'store_by_id', 'store_by_name')

    def __init__(self):
        self.store_by_token: Dict[str, 'Player'] = {}
        self.store_by_id: Dict[int, 'Player'] = {}
        self.store_by_name: Dict[str, 'Player'] = {}

    def add_token(self, player: 'Player') -> bool:
        if player.id in self.store_by_id or \
                player.token in self.store_by_token or \
                player.safe_name in self.store_by_name:
            return False

        self.store_by_token[player.token] = player
        self.store_by_id[player.id] = player
        self.store_by_name[player.safe_name] = player
        return True

    def get_token(self, uid: int = None, token: str = None, name: str = None) -> Union[Union['Player', 'TourneyPlayer'],
                                                                                       None]:
        if uid:  # if uid presents
            return self.store_by_id.get(uid, None)

        if token:
            if not self.store_by_token.get(token, None):
                # we can't find token, but probably it's additional client?!
                for (_, user) in self.store_by_token.items():
                    if hasattr(user, "additional_clients"):
                        if token in user.additional_clients:
                            return user.additional_clients.get(token, None)

                        continue

            return self.store_by_token.get(token, None)

        if name:
            return self.store_by_name.get(name, None)

        return None

    def delete_token(self, token: 'Player') -> bool:
        if token.is_tourneymode:
            for (_, user) in self.store_by_token.items():
                if hasattr(user, "additional_clients"):
                    if token.token in user.additional_clients:
                        user.additional_clients.pop(token.token)

        if (token.id not in self.store_by_id or
                token.token not in self.store_by_token or
                token.safe_name not in self.store_by_name):
            return False

        res = (self.store_by_token.pop(token.token, False) and self.store_by_id.pop(token.id, False) and
               self.store_by_name.pop(token.safe_name, False))
        token.token = ''
        return res

    def get_all_tokens(self, ignore_tournament_clients: bool = False) -> List['Player']:
        normal_tokens = [v for (k, v) in self.store_by_token.items()]  # just return all player instances
        additional_tokens = []
        if not ignore_tournament_clients:
            for (_, user) in self.store_by_token.items():
                if hasattr(user, "additional_clients"):
                    additional_tokens.extend([token for (_, token) in user.additional_clients.items()])

        normal_tokens.extend(additional_tokens)
        return normal_tokens
