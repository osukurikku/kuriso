from typing import TYPE_CHECKING
from starlette.requests import Request
from starlette.responses import JSONResponse
from handlers.decorators import HttpEvent
from blob import Context
from helpers import http_utils
from objects.constants import Privileges
from objects.constants.KurikkuPrivileges import KurikkuPrivileges
from packets.Builder.index import PacketBuilder

if TYPE_CHECKING:
    from objects.Channel import Channel


@HttpEvent.register_handler('/api/delta/ping', methods=['GET'])
async def delta_ping(request: Request):
    return JSONResponse({
        'code': 200,
        'version': Context.version
    })


@HttpEvent.register_handler('/api/delta/clients/{api_id:str}/rtx', methods=['GET'])
async def delta_clients_user_alert(_):
    return {
        "code": 418,
        "message": "rtx is deprecated"
    }


@HttpEvent.register_handler('/api/delta/chat_channels', methods=['GET'])
async def delta_chat_channels(request: Request):
    privileges = await http_utils.resolve_privileges(request)
    response = []

    private = False
    if 'private' in request.query_params:
        if request.query_params.get('private', '0').isdigit():
            private = bool(request.query_params.get('private', 0))
    public = False
    if 'public' in request.query_params:
        if request.query_params.get('public', '0').isdigit():
            public = bool(request.query_params.get('public', 0))
    permanent = False
    if 'permanent' in request.query_params:
        if request.query_params.get('permanent', '0').isdigit():
            permanent = bool(request.query_params.get('permanent', 0))
    else:
        temporary = False
        if 'temporary' in request.query_params:
            if request.query_params.get('temporary', '0').isdigit():
                temporary = bool(request.query_params.get('temporary', 0))
        is_all = not any([private, public, permanent, temporary])
        if is_all:
            for _, channel in Context.channels.items():
                if not channel.can_read:
                    if not privileges & Privileges.ADMIN_CHAT_MOD > 0:
                        continue
                response.append(channel.to_delta())

        else:
            for _, channel in Context.channels.items():
                if not channel.can_read:
                    if not privileges & Privileges.ADMIN_CHAT_MOD > 0:
                        continue
                    else:
                        if temporary:
                            if channel.temp_channel:
                                response.append(channel.to_delta())
                                continue
                        if permanent:
                            if not channel.temp_channel:
                                response.append(channel.to_delta())
                                continue
                        if private:
                            if not channel.can_read:
                                response.append(channel.to_delta())
                                continue
                    if public and channel.can_read and channel.can_write:
                        response.append(channel.to_delta())
                        continue

    return JSONResponse(response)


@HttpEvent.register_handler('/api/delta/chat_channels/{chan_name}', methods=['GET'])
async def delta_chat_channel(request: Request):
    if 'chan_name' not in request.path_params:
        return JSONResponse({
            'code': 404,
            'message': 'Resource not found (no such channel)'
        }, status_code=404)
    else:
        proper_chan_name = request.path_params.get('chan_name', '')
        if not proper_chan_name.startswith('#'):
            proper_chan_name = '#' + proper_chan_name

        chan = Context.channels.get(proper_chan_name, False)
        if not chan:
            return JSONResponse({
                'code': 404,
                'message': 'Resource not found (no such channel)'
            }, status_code=404)

        if not chan.can_read:
            privileges = await http_utils.resolve_privileges(request)
            if not privileges & Privileges.ADMIN_CHAT_MOD > 0:
                return JSONResponse({
                    'code': 403,
                    'message': "You don't have enough privileges to see this channel's information"
                }, status_code=403)
        return JSONResponse(chan.to_delta())


@HttpEvent.register_handler('/api/delta/chat_channels/{chan_name}', methods=['POST'])
async def delta_chat_channels_moderated(_):
    return JSONResponse({
        'code': 200,
        'message': "We haven't moderated channel status!"
    })


@HttpEvent.register_handler('/api/delta/clients', methods=['GET'])
async def delta_clients(_):
    users = Context.players.get_all_tokens()
    clients_response = {}
    for client in users:
        clients_response[client.id] = client.to_delta()

    return {
        "code": 200,
        "clients": clients_response,
        "connected_clients": len(users),  # TODO: Make count of clients proper, when IRC server released
        "connected_users": len(users)
    }


@HttpEvent.register_handler('/api/delta/clients/{user:int}', methods=['GET'])
async def delta_clients_user_int(request: Request):
    user_id = request.path_params.get("user", 0)
    user = Context.players.get_token(uid=user_id)
    response = []
    if user:
        response.append(user.to_delta())

    return {
        "clients": response,
        "code": 200,
    }


@HttpEvent.register_handler('/api/delta/clients/{user:str}', methods=['GET'])
async def delta_clients_user_str(request: Request):
    user_safe_name = request.path_params['user']
    user = Context.players.get_token(name=user_safe_name)
    if not user:
        return {
            "code": 404,
            "message": "Either an api identifier (safe user name) or a user id must be provided.\n"
                       "You must provide a valid user id"
        }

    response: dict = user.to_delta()
    response['code'] = 200
    return response


@HttpEvent.register_handler('/api/delta/clients/{api_id:str}/join_match', methods=['GET'])
async def delta_clients_user_join_match(request: Request):
    privileges = await http_utils.resolve_privileges(request)
    if not (privileges & Privileges.ADMIN_MANAGE_USERS > 0):
        return {
            "code": 401,
            "message": "You haven't enough permissions to manage users!"
        }

    api_id = request.path_params.get("api_id", None)

    match_not_found_error = {
        "code": 404,
        "message": "Match can't be found, try one more time..."
    }

    try:
        match_id = (await request.json()).get("match_id", None)
        if not match_id or match_id and not match_id.isdigit():
            return match_not_found_error
    except Exception as e:
        print(e)
        return match_not_found_error

    match = Context.matches.get(match_id, None)
    if not match:
        return match_not_found_error

    user = Context.players.get_token(name=api_id)
    if not api_id or not user or user.is_tourneymode:
        return {
            "code": 404,
            "message": "There’s no client with such API Identifier, or the client is not a game client."
        }

    cant_error = {
        "code": 409,
        "message": "The provided client could not be added to the multiplayer match "
                   "(the match is full, the client is already in a multiplayer match)."
    }
    if user.match or not await match.join_player(user):
        return cant_error

    return {
        "code": 200,
        "message": f"{user.safe_name} has joined the match."
    }


@HttpEvent.register_handler('/api/delta/clients/{api_id:str}/alert', methods=['GET'])
async def delta_clients_user_alert(request: Request):
    privileges = await http_utils.resolve_privileges(request)
    if not (privileges & Privileges.ADMIN_MANAGE_USERS > 0):
        return {
            "code": 401,
            "message": "You haven't enough permissions to manage users!"
        }

    api_id = request.path_params.get("api_id", None)
    user = Context.players.get_token(name=api_id)
    if not user:
        return {
            "code": 404,
            "message": "There’s no client with such API Identifier, or the client is not a game client.",
        }

    try:
        message = (await request.json()).get("message", None)
        if not message:
            return {
                "code": 400,
                "message": "Message is empty! Provide it correctly."
            }
    except Exception as e:
        print(e)
        return {
            "code": 500,
            "message": "Something goes wrong! Write to KotRik ASAP."
        }

    notify_packet = await PacketBuilder.Notification(message)
    user.enqueue(notify_packet)
    return {
        "code": 200,
        "message": f"Alert sent successfully to {user.safe_name}"
    }