from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate

from bot.bot import CrystalBot
from handlers.wshandlers.wsRegistry import WebsocketHandlers
from lib.websocket_formatter import WebsocketEvents, WebsocketEvent
from objects.BanchoObjects import Message

SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string", "minLength": 1, "maxLength": 2048},
        "to": {"type": "string", "minLength": 1, "maxLength": 16},
    },
    "required": ["message", "to"],
}


async def sendMessage(player, data):
    # object validation
    try:
        validate(instance=data, schema=SCHEMA)
    except ValidationError as e:
        return await player.websocket.send_json(WebsocketEvent.failed_message(e.message))

    channel = data["to"].startswith("#")
    # prepare message
    safe_to = data["to"].lower().strip().replace(" ", "_")
    message = Message(sender=player.name, body=data["message"], to=safe_to, client_id=player.id)
    send_corountine = player.send_message(message)
    if not channel:
        if data["to"] == CrystalBot.bot_name:
            await CrystalBot.proceed_command(message)
            return True
        return await send_corountine

    # send into kuriso
    await CrystalBot.proceed_command(message)
    return await send_corountine


WebsocketHandlers().set_handler(WebsocketEvents.SEND_MESSAGE, sendMessage)
