from collections import namedtuple


class Message:

    __slots__ = ('sender', 'to', 'body', 'client_id')

    def __init__(self, sender: str = '', to: str = '', body: str = '', client_id: int = 0):
        self.sender: str = sender
        self.to: str = to
        self.body: str = body
        self.client_id: int = client_id
