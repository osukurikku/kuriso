import queue
from typing import Optional


class Token:

    def __init__(self, token: str):
        self.token = token
        self.queue = queue.Queue()

    @property
    def is_queue_empty(self):
        return self.queue.empty()

    def enqueue(self, b: bytes) -> None:
        self.queue.put_nowait(b)

    def dequeue(self) -> Optional[bytes]:
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            pass