from starlette.responses import PlainTextResponse

from handlers.decorators import HttpEvent


@HttpEvent.register_handler("/web/bancho-connect.php", methods=["GET"])
async def main_handler(_):
    return PlainTextResponse("ru")
