import asyncio
import time

from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState
from blob import Context
from handlers.wshandlers.wsRegistry import WebsocketHandlers
from helpers import userHelper
from lib import logger
from lib.websocket_formatter import WebsocketEvent, WebsocketEvents
from objects.WebsocketPlayer import WebsocketPlayer
from objects.constants import Privileges
from packets.Builder.index import PacketBuilder


async def websocket_endpoint(websocket: WebSocket):
    auth_header = websocket.headers.get("Authorization")
    if not auth_header:
        return await websocket.close(
            code=3000,
        )

    token = auth_header.split(" ")
    if len(token) < 2:
        return await websocket.close(
            code=3000,
        )
    token = token[-1]
    user = await Context.mysql.fetch(
        f"SELECT tokens.user as uid, users.username FROM tokens INNER JOIN users ON users.id = tokens.user WHERE token = %s",
        [token],
    )
    if not user:
        return await websocket.close(
            code=3000,
        )

    await websocket.accept()

    start_data = await userHelper.get_start_user(user["username"])
    if not start_data:
        # await websocket.send_json(WebsocketEvent.error_disconnect("server error uwu"))
        logger.elog(
            f"[rejected/{start_data['username']}] Was attempt to connect ws!chat but server returned nothin data for stats"
        )
        await websocket.send_json(WebsocketEvent.error_disconnect("server error uwu"))
        return await websocket.close(code=3000)

    # checking for user correct privileges at least equals 3 (NORMAL|PUBLIC)
    is_user_valid = (
        start_data["privileges"] & Privileges.USER_PUBLIC
        and start_data["privileges"] & Privileges.USER_NORMAL
    )

    if not is_user_valid:
        logger.elog(f"[rejected/{start_data['username']}] Restricted. Attempt to ws!chat")
        await websocket.send_json(
            WebsocketEvent.error_disconnect(
                "User hasn't proper privileges (restricted or banned)"
            )
        )
        return await websocket.close(code=3000)

    pToken = Context.players.get_token(uid=start_data["id"])
    if hasattr(pToken, "websocket"):
        logger.elog(
            f"[{pToken.token}/{start_data['username']}] was already connected to ws!chat. Disconnecting!"
        )
        await pToken.logout()
        pToken = None

    player = None
    start_params = {
        "user_id": int(start_data["id"]),
        "user_name": start_data["username"],
        "privileges": start_data["privileges"],
        "utc_offset": 0,
        "pm_private": False,
        "silence_end": 0
        if start_data["silence_end"] - int(time.time()) < 0
        else start_data["silence_end"] - int(time.time()),
        "is_tourneymode": False,
        "ip": websocket.client.host,
        "socket": websocket,
    }
    if pToken and pToken.is_tourneymode:
        # check if clients have correct order
        if not hasattr(pToken, "additional_clients"):
            await websocket.send_json(
                WebsocketEvent.error_disconnect(
                    "Your tourney instance isn't connected to kuriso right now"
                )
            )
            return await websocket.close(code=3000)

        start_params["is_tourneymode"] = True
        # AND WE'RE READY TO GO!
        player = WebsocketPlayer(**start_params)
        pToken.add_additional_client(player, token)
    elif pToken:
        logger.elog(
            f"[{pToken.token}/{start_data['username']}] attempt to connect to ws!chat, but logged in osu!"
        )
        return await websocket.close(code=3000)
    else:
        # AND WE'RE READY TO GO!
        player = WebsocketPlayer(**start_params)
        Context.players.add_token(player)

    for p in Context.players.get_all_tokens():
        if p.is_restricted:
            continue

        if hasattr(p, "websocket"):
            await p.websocket.send_json(WebsocketEvent.user_joined(player.id))
            continue

        p.enqueue(
            bytes(
                await PacketBuilder.UserPresence(player) + await PacketBuilder.UserStats(player)
            )
        )

    await asyncio.gather(
        *[
            player.parse_friends(),
            player.update_stats(),
            player.parse_country(websocket.client.host),
        ]
    )
    logger.klog(f"[{player.token}/{start_data['username']}] logged in, through ws!chat")

    await websocket.send_json(WebsocketEvent.welcome_message(player))

    try:
        while True:
            if player.is_socket_closing:
                break

            next = await websocket.receive_json()
            if "event" not in next or "data" not in next:
                continue

            event_function = WebsocketHandlers().get_handler(next["event"])
            if not event_function:
                continue

            await event_function(player, next["data"])
    except WebSocketDisconnect as d:
        if d.code == 1000:
            await player.logout()
            logger.klog(
                f"[{player.token}/{player.name}] Disconnected from ws!chat. code {d.code}"
            )
        else:
            await player.logout()
            logger.klog(
                f"[{player.token}/{player.name}] Disconnected from ws!chat. code {d.code}"
            )
    else:
        # for case, if user dead in unexpected case idk what can happend :/
        if websocket.client_state == WebSocketState.DISCONNECTED:
            return
