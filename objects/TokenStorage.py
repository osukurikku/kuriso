from typing import Union, TYPE_CHECKING
if TYPE_CHECKING:
    from objects.Player import Player


class TokenStorage:
    __slots__ = ('store_by_token', 'store_by_id', 'store_by_name')

    def __init__(self):
        self.store_by_token = {}
        self.store_by_id = {}
        self.store_by_name = {}

    def add_token(self, player: 'Player') -> bool:
        if player.id in self.store_by_id or \
                player.token in self.store_by_token or \
                player.name in self.store_by_name:
            return False

        self.store_by_token[player.token] = player
        self.store_by_id[player.id] = player
        self.store_by_name[player.name] = player
        return True

    def get_token(self, uid: int = None, token: str = None, name: str = None) -> Union['Player', None]:
        if uid:  # if uid presents
            return self.store_by_id.get(uid, None)

        if token:
            return self.store_by_token.get(token, None)

        if name:
            return self.store_by_name.get(name, None)

        return None

    def delete_token(self, token: 'Player') -> bool:
        if (token.id not in self.store_by_id or
                token.token not in self.store_by_token or
                token.name not in self.store_by_name):
            return False
        res = (self.store_by_token.pop(token.token, False) and self.store_by_id.pop(token.id, False) and
               self.store_by_name.pop(token.name, False))
        token.token = ''
        return res

    def get_all_tokens(self):
        return [v for (k, v) in self.store_by_token.items()]  # just return all player instances
