class HttpEvent:

    handlers = {}

    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(HttpEvent, cls).__new__(cls)
        return cls.instance

    @classmethod
    def register_handler(cls, path: str, methods=None):
        if methods is None:
            methods = ["GET"]

        def wrapper(func):
            cls.handlers[path] = {"methods": methods, "func": func}

        return wrapper
