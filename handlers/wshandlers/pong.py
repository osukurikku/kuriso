import time

from handlers.wshandlers.wsRegistry import WebsocketHandlers
from lib.websocket_formatter import WebsocketEvents


async def pong(player, __):
    player.last_packet_unix = int(time.time())
    return True


WebsocketHandlers().set_handler(WebsocketEvents.PONG, pong)
