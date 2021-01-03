from starlette.responses import HTMLResponse

from handlers.decorators import HttpEvent


@HttpEvent.register_handler("/{path:str}", methods=['GET', 'POST'])
async def _(_):
    return HTMLResponse("<html>not found</html>", status_code=404)
