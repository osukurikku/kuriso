from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate

from blob import Context
from handlers.wshandlers.wsRegistry import WebsocketHandlers
from lib import logger
from lib.websocket_formatter import WebsocketEvents, WebsocketEvent

SCHEMA = {
    "type": "object",
    "properties": {"channel_name": {"type": "string"}},
    "required": ["channel_name"],
}


async def joinChannel(player, data):
    # object validation
    try:
        validate(instance=data, schema=SCHEMA)
    except ValidationError as e:
        return await player.websocket.send_json(WebsocketEvent.failed_message(e.message))

    if not data["channel_name"].startswith("#"):
        return

    chan: "Channel" = Context.channels.get(data["channel_name"], None)
    if not chan:
        logger.elog(f"[{player.name}] Failed to join in {data['channel_name']}")
        return False

    # send into kuriso
    return await chan.join_channel(player)


WebsocketHandlers().set_handler(WebsocketEvents.JOIN_CHANNEL, joinChannel)
