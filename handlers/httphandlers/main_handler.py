import asyncio
import time
import datetime

from bot.bot import CrystalBot
from lib import logger
from starlette.requests import Request
from starlette.responses import HTMLResponse

from handlers.decorators import HttpEvent, OsuEvent
from lib.BanchoResponse import BanchoResponse
from blob import Context
from lib.logger import magnitude_fmt_time
from objects.constants import Privileges
from objects.constants.KurikkuPrivileges import KurikkuPrivileges
from objects.Player import Player
from packets.Builder.index import PacketBuilder
from packets.OsuPacketID import OsuPacketID
from packets.Reader.index import KurisoPacketReader
from helpers import userHelper

ALLOWED_RESTRICT_PACKETS = [
    OsuPacketID.Client_Exit.value,
    OsuPacketID.Client_UserStatsRequest.value,
    OsuPacketID.Client_RequestStatusUpdate.value,
    OsuPacketID.Client_UserPresenceRequest.value,
    OsuPacketID.Client_SendUserStatus.value,
    OsuPacketID.Client_ChannelJoin.value,
    OsuPacketID.Client_ChannelLeave.value,
]  # these packets available in restrict mode

# don't log these packets due to much noise :/
DONT_LOG_PACKETS = [
    OsuPacketID.Client_SpectateFrames.value,
    OsuPacketID.Client_MatchScoreUpdate.value,
]


@HttpEvent.register_handler("/", methods=["GET", "POST"])
async def main_handler(request: Request):
    if request.headers.get("user-agent", "") != "osu!" or request.method == "GET":
        return HTMLResponse(f"<html>{Context.motd_html}</html>")

    token = request.headers.get("osu-token", None)
    if token:
        if not (token_object := Context.players.get_token(token=token)):
            # send to re-login, because token doesn't exists in storage
            response = PacketBuilder.UserID(-5)
            return BanchoResponse(response)

        token_object.last_packet_unix = int(time.time())

        # packets recieve
        with memoryview(await request.body()) as packets:
            raw_bytes = KurisoPacketReader(packets)
            response = bytes()
            while not raw_bytes.EOF():
                packet_id = raw_bytes.read_u_int_16()
                _ = raw_bytes.read_int_8()  # empty byte
                packet_length = raw_bytes.read_int_32()

                if packet_id == OsuPacketID.Client_Pong.value:
                    # client just spamming it and tries to say, that he is normal :sip:
                    continue

                data = raw_bytes.slice_buffer(packet_length)

                if token_object.is_restricted and packet_id not in ALLOWED_RESTRICT_PACKETS:
                    logger.wlog(
                        f"[{token_object.token}/{token_object.name}] Ignored packet {packet_id}(account restrict)",
                    )
                    continue

                if packet_id in OsuEvent.handlers:
                    # This packet can be handled by OsuEvent Class, call it now!
                    # Oh wait let go this thing in async executor.
                    start_time = time.perf_counter_ns()
                    await OsuEvent.handlers[packet_id](data, token_object)
                    end_time = time.perf_counter_ns()
                    if packet_id not in DONT_LOG_PACKETS:
                        logger.klog(
                            f"<{token_object.name}> Has triggered {OsuPacketID(packet_id)} with packet length: {packet_length} | Request took: {magnitude_fmt_time(end_time - start_time)}",
                        )
                else:
                    logger.wlog(f"[Events] Packet ID: {packet_id} not found in events handlers")

        response += token_object.dequeue()

        response = BanchoResponse(bytes(response), token=token_object.token)
        return response

    # --- FISRT LOGIN ON KURISO INCOMING ---
    # Structure (new line = "|", already split)
    # [0] osu! version
    # [1] plain mac addressed, separated by "."
    # [2] mac addresses hash set
    # [3] unique ID
    # [4] disk ID
    start_time = time.perf_counter_ns()  # auth speed benchmark time

    loginData = (await request.body()).decode().split("\n")
    if len(loginData) < 3:
        return BanchoResponse(PacketBuilder.UserID(-5))

    if not await userHelper.check_login(loginData[0], loginData[1], request.client.host):
        logger.elog(f"[{loginData[0]}] tried to login but failed with password")
        return BanchoResponse(PacketBuilder.UserID(-1))

    # auth speed benchmark time
    user_data = await userHelper.get_start_user(loginData[0])
    if not user_data:
        return BanchoResponse(PacketBuilder.UserID(-1))

    data = loginData[2].split("|")
    hashes = data[3].split(":")[:-1]
    time_offset = int(data[1])
    pm_private = data[4] == "1"

    is_tourney = "tourney" in data[0]

    # check if user already on kuriso
    if Context.players.get_token(uid=user_data["id"]) and not is_tourney:
        # wtf osu
        await Context.players.get_token(uid=user_data["id"]).logout()

    if (
        user_data["privileges"] & Privileges.USER_PENDING_VERIFICATION
    ) or not await userHelper.user_have_hardware(user_data["id"]):
        # we need to verify our user
        is_success_verify = await userHelper.activate_user(
            user_data["id"],
            user_data["username"],
            hashes,
        )
        if not is_success_verify:
            response = PacketBuilder.UserID(-1) + PacketBuilder.Notification(
                "Your HWID is not clear. Contact Staff to create account!",
            )
            return BanchoResponse(bytes(response))

        user_data = await userHelper.get_start_user(loginData[0])

    await userHelper.logHardware(user_data["id"], hashes)

    if (user_data["privileges"] & KurikkuPrivileges.Normal) != KurikkuPrivileges.Normal and (
        user_data["privileges"] & Privileges.USER_PENDING_VERIFICATION
    ) == 0:
        logger.elog(f"[{loginData}] Banned chmo tried to login")
        response = PacketBuilder.UserID(-1) + PacketBuilder.Notification(
            "You are banned. Join our discord for additional information.",
        )

        return BanchoResponse(bytes(response))

    if (
        not user_data["privileges"] & Privileges.USER_PUBLIC
        and user_data["privileges"] & Privileges.USER_NORMAL
    ) and not user_data["privileges"] & Privileges.USER_PENDING_VERIFICATION:
        logger.elog(f"[{loginData}] Locked dude tried to login")
        response = PacketBuilder.UserID(-1) + PacketBuilder.Notification(
            "You are locked by staff. Join discord and ask for unlock!",
        )

        return BanchoResponse(bytes(response))

    if bool(Context.bancho_settings["bancho_maintenance"]):
        # send to user that maintenance
        if not user_data["privileges"] & Privileges.ADMIN_MANAGE_SERVERS:
            response = PacketBuilder.UserID(-1) + PacketBuilder.Notification(
                "Kuriso! is in maintenance mode. Please try to login again later.",
            )

            return BanchoResponse(bytes(response))

    osu_version = data[0]
    await userHelper.setUserLastOsuVer(user_data["id"], osu_version)
    osu_version_int = osu_version[1:9]
    if not osu_version_int.isdigit():
        return BanchoResponse(PacketBuilder.UserID(-1))

    now = datetime.datetime.now()
    vernow = datetime.datetime(
        int(osu_version_int[:4]),
        int(osu_version_int[4:6]),
        int(osu_version_int[6:8]),
        00,
        00,
    )
    deltanow = now - vernow

    if (
        not osu_version_int[0].isdigit()
        or deltanow.days > 360
        or int(osu_version_int) < 20200811
    ):
        response = PacketBuilder.UserID(-2) + PacketBuilder.Notification(
            "Sorry, you use outdated/bad osu!version. Please update your game to join server",
        )
        return BanchoResponse(bytes(response))

    player_start_params = dict(
        user_id=int(user_data["id"]),
        user_name=user_data["username"],
        privileges=user_data["privileges"],
        utc_offset=time_offset,
        pm_private=pm_private,
        silence_end=0
        if user_data["silence_end"] - int(time.time()) < 0
        else user_data["silence_end"] - int(time.time()),
        is_tourneymode=False,
        ip=request.client.host,
    )
    player = None
    if is_tourney:
        u_token = Context.players.get_token(uid=user_data["id"])
        if hasattr(u_token, "irc"):
            await u_token.logout()
            u_token = None

        if u_token:
            # manager was logged before, we need just add additional token
            token, player = Context.players.get_token(
                uid=user_data["id"],
            ).add_additional_client()
        else:
            player_start_params["is_tourneymode"] = True

    if not player:
        # create Player instance finally!!!!
        player = Player(**player_start_params)

    await asyncio.gather(
        *[
            player.parse_friends(),
            player.update_stats(),
            player.parse_country(request.client.host),
        ]
    )

    if "ppy.sh" in request.url.netloc and not (player.is_admin or player.is_tournament_stuff):
        return BanchoResponse(
            bytes(
                PacketBuilder.UserID(-5)
                + PacketBuilder.Notification(
                    "Sorry, you use outdated connection to server. Please use devserver flag",
                ),
            ),
        )

    user_country = await userHelper.get_country(user_data["id"])
    if user_country == "XX":
        await userHelper.set_country(user_data["id"], player.country[1])

    start_bytes = [
        PacketBuilder.UserID(player.id),
        PacketBuilder.ProtocolVersion(19),
        PacketBuilder.BanchoPrivileges(player.bancho_privs),
        PacketBuilder.UserPresence(player),
        PacketBuilder.UserStats(player),
        PacketBuilder.FriendList(player.friends),
        PacketBuilder.SilenceEnd(player.silence_end if player.silence_end > 0 else 0),
        PacketBuilder.Notification(
            f"""Welcome to kuriso!\nBuild ver: v{Context.version}\nCommit: {Context.commit_id}""",
        ),
    ]
    end_time = time.perf_counter_ns()
    start_bytes.append(
        PacketBuilder.Notification(
            f"Authorization took: {magnitude_fmt_time(end_time - start_time)}",
        ),
    )
    start_bytes = b"".join(start_bytes)

    if Context.bancho_settings.get("login_notification", None):
        start_bytes += PacketBuilder.Notification(
            Context.bancho_settings.get("login_notification", None),
        )

    if Context.bancho_settings.get("bancho_maintenance", None):
        start_bytes += PacketBuilder.Notification(
            "Don't forget enable server after maintenance :sip:",
        )

    if Context.bancho_settings["menu_icon"]:
        start_bytes += PacketBuilder.MainMenuIcon(Context.bancho_settings["menu_icon"])

    if is_tourney and Context.players.get_token(uid=user_data["id"]):
        logger.klog(f"<{player.name}> Joined kuriso as additional client for origin!")
        for p in Context.players.get_all_tokens():
            if p.is_restricted:
                continue

            start_bytes += bytes(PacketBuilder.UserPresence(p) + PacketBuilder.UserStats(p))
    else:
        for p in Context.players.get_all_tokens():
            if p.is_restricted:
                continue

            start_bytes += bytes(PacketBuilder.UserPresence(p) + PacketBuilder.UserStats(p))
            p.enqueue(
                bytes(PacketBuilder.UserPresence(player) + PacketBuilder.UserStats(player)),
            )

        await userHelper.saveBanchoSession(player.id, request.client.host)

        Context.players.add_token(player)
        await Context.redis.set(
            "ripple:online_users",
            len(Context.players.get_all_tokens(True)),
        )
        logger.klog(f"<{player.name}> Joined kuriso!")

    # default channels to join is #osu, #announce and #english
    await asyncio.gather(
        *[
            Context.channels["#osu"].join_channel(player),
            Context.channels["#announce"].join_channel(player),
            Context.channels["#english"].join_channel(player),
        ]
    )

    for (_, chan) in Context.channels.items():
        if not chan.temp_channel and chan.can_read:
            start_bytes += PacketBuilder.ChannelAvailable(chan)

    start_bytes += PacketBuilder.ChannelListeningEnd()

    if player.is_restricted:
        start_bytes += PacketBuilder.UserRestricted()
        await CrystalBot.ez_message(
            player.name,
            "Your account is currently in restricted mode. Please visit kurikku's website for more information.",
        )

    Context.stats["osu_versions"].labels(osu_version=osu_version).inc()
    Context.stats["devclient_usage"].labels(host=request.url.netloc).inc()
    return BanchoResponse(start_bytes, player.token)
