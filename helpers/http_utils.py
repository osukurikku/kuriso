from starlette.requests import Request
from blob import Context
from objects.constants.KurikkuPrivileges import KurikkuPrivileges


async def resolve_privileges(request: Request) -> int:
    token = None
    if 'token' in request.query_params:
        token = request.query_params.get('token', None)

    if 'X-Ripple-Token' in request.headers:
        token = request.headers.get('X-Ripple-Token', None)

    if 'rt' in request.cookies:
        token = request.cookies.get('rt', None)

    if not token:
        return 0

    db_result = await Context.mysql.fetch(
        "SELECT users.privileges FROM users INNER JOIN tokens ON tokens.token = ? WHERE users.id = tokens.user",
        [token]
    )
    if not db_result:
        return 0

    return KurikkuPrivileges(db_result['privileges'])
