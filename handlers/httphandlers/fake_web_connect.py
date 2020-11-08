from starlette.requests import Request
from starlette.responses import PlainTextResponse

from handlers.decorators import HttpEvent


@HttpEvent.register_handler("/web/bancho-connect.php", methods=['GET'])
async def main_handler(request: Request):
    return PlainTextResponse("ru")