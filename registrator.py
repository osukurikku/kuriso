from starlette.applications import Starlette
from starlette.routing import Route, Router, WebSocketRoute

import sys
import os

from blob import Context
from handlers.decorators import HttpEvent
from handlers.websocket_handler import websocket_endpoint
from lib import logger
from objects.Channel import Channel


def load_handlers(app: Starlette):
    logger.wlog("[Handlers/Events] Loading handlers & events...")
    paths_to_import = {"handlers": ["httphandlers", "eventhandlers"]}

    for (k, v) in paths_to_import.items():
        sys.path.insert(0, k)
        for deep_path in v:
            sys.path.insert(0, f"{k}/{deep_path}")
            folder_files = os.listdir(f"{k}/{deep_path}")

            for file in folder_files:
                if file.endswith(".py"):
                    logger.slog(f"[Handlers/Events] file {file} loaded! ")
                    sys.path.insert(0, f"{k}/{deep_path}/{file}")
                    __import__(os.path.splitext(file)[0], None, None, [""])

    handlers = []
    for (path, path_describe) in HttpEvent.handlers.items():
        logger.slog(f"[Handlers/Events] {path} registered!")
        handlers.append(
            Route(
                path,
                endpoint=path_describe["func"],
                methods=path_describe["methods"],
            )
        )

    handlers.append(WebSocketRoute("/api/chat/ws", endpoint=websocket_endpoint))
    app.mount("", Router(handlers))

    # app.add_websocket_route("", websocket_endpoint)
    # app.mount("/api/chat/ws", websocket_endpoint)
    return True


async def load_default_channels():
    async for channel in Context.mysql.iterall(
        "select name as server_name, description, public_read, public_write from bancho_channels"
    ):
        if channel["server_name"] in Context.channels:
            continue

        Context.channels[channel["server_name"]] = Channel(**channel)

        logger.slog(f"[Channels] Create channel {channel['server_name']}")
