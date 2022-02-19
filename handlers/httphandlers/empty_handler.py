from starlette.responses import HTMLResponse

from handlers.decorators import HttpEvent


@HttpEvent.register_handler("/{path:str}", methods=["GET", "POST"])
async def _(_):
    return HTMLResponse("<pre>not found</pre>", status_code=404)
