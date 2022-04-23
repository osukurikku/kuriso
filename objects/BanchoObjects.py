import time


class Message:

    __slots__ = ("sender", "to", "body", "client_id", "when")

    def __init__(self, sender: str = "", to: str = "", body: str = "", client_id: int = 0):
        self.sender = sender
        self.to = to
        self.body = body
        self.client_id = client_id
        self.when = int(time.time())
