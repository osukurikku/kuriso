from typing import Callable, Union


class WebsocketHandlers(object):
    handlers = {}

    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(WebsocketHandlers, cls).__new__(cls)
        return cls.instance

    def set_handler(cls, event_name: str, event_func: Callable) -> bool:
        if not event_name:
            return False

        cls.handlers[event_name] = event_func
        return True

    def get_handler(cls, event_name) -> Union[Callable, None]:
        return cls.handlers.get(event_name, None)
