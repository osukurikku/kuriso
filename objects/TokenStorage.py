from typing import Union

from objects.Player import Player


class TokenStorage:
    __slots__ = ('store_by_token', 'store_by_id')

    def __init__(self):
        self.store_by_token = {}
        self.store_by_id = {}

    def add_token(self, player: Player) -> bool:
        if player.id in self.store_by_id or \
                player.token in self.store_by_token:
            return False

        self.store_by_token[player.token] = player
        self.store_by_id[player.id] = player

    def get_token(self, uid: int = None, token: str = None) -> Union[Player, None]:
        if uid:  # if uid presents
            return self.store_by_id.get(uid, None)

        if token:
            return self.store_by_token.get(token, None)

        return None

    def delete_token(self, token: Player) -> bool:
        if not token.id in self.store_by_id or \
                not token.token in self.store_by_token:
            return False

        return self.store_by_token.pop(token.token, False) and self.store_by_id.pop(token.id, False)

    def get_all_tokens(self):
        return [v for (k, v) in self.store_by_token.items()] # just return all player instances