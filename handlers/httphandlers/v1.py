from starlette.requests import Request
from starlette.responses import JSONResponse

from blob import Context
from bot.bot import CrystalBot
from config import Config
from handlers.decorators import HttpEvent
from helpers import userHelper
from objects.constants.KurikkuPrivileges import KurikkuPrivileges


@HttpEvent.register_handler("/api/v1/isOnline", methods=["GET"])
async def isOnline_handler(request: Request):
    token = None
    if request.query_params.get("u", None):
        safe_name = request.query_params["u"].lower().strip().replace(" ", "_")
        token = Context.players.get_token(name=safe_name)

    _id = request.query_params.get("id", None)
    if _id and _id.isdigit():
        token = Context.players.get_token(uid=int(_id))

    return JSONResponse({"code": 200, "result": bool(token), "message": "ok"})


@HttpEvent.register_handler("/api/v1/onlineUsers", methods=["GET"])
async def onlineUsers_handler(_):
    return JSONResponse(
        {
            "status": 200,
            "result": len(Context.players.get_all_tokens(ignore_tournament_clients=True)),
            "message": "ok",
        },
    )


@HttpEvent.register_handler("/api/v1/fokabotMessage", methods=["GET"])
async def CrystalMessage_handler(request: Request):
    if not all(key in request.query_params for key in ["k", "to", "msg"]):
        return JSONResponse({"status": 400, "message": "invalid parameters"})

    _k = request.query_params.get("k", "")
    if _k != Config.config["host"]["ci_key"]:
        return JSONResponse({"status": 400, "message": "invalid ci key"})

    await CrystalBot.ez_message(
        request.query_params.get("to").encode().decode("ASCII", "ignore"),
        request.query_params.get("msg").encode().decode("ASCII", "ignore"),
    )

    return JSONResponse({"status": 200, "message": "ok"})


@HttpEvent.register_handler("/api/v1/verifiedStatus", methods=["GET"])
async def verifiedStatus_handler(request: Request):
    if "u" not in request.query_params or not request.query_params.get("u", "").isdigit():
        return JSONResponse({"status": 400, "result": -1, "message": "invalid parameters"})

    # I don't have verified cache, that's means we need use something another
    verifiedStatus = -1

    user_data = await userHelper.get_start_user_id(int(request.query_params.get("u")))
    if (
        user_data
        and (user_data["privileges"] & KurikkuPrivileges.Normal) == KurikkuPrivileges.Normal
    ):
        verifiedStatus = 1

    return JSONResponse({"status": 200, "result": verifiedStatus, "message": "ok"})
