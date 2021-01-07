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
from objects.TourneyPlayer import TourneyPlayer
from objects.constants import Privileges
from objects.constants.KurikkuPrivileges import KurikkuPrivileges
from objects.Player import Player
from packets.Builder.index import PacketBuilder
from packets.OsuPacketID import OsuPacketID
from packets.Reader.index import KorchoBuffer
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


@HttpEvent.register_handler("/", methods=['GET', 'POST'])
async def main_handler(request: Request):
    if request.headers.get("user-agent", "") != "osu!":
        return HTMLResponse(f"<html>{Context.motd_html}</html>")

    token = request.headers.get("osu-token", None)
    if token:
        if token == '':
            response = await PacketBuilder.UserID(-5)
            return BanchoResponse(response)  # send to re-login

        token_object = Context.players.get_token(token=token)
        if not token_object:
            # send to re-login, because token doesn't exists in storage
            response = await PacketBuilder.UserID(-5)
            return BanchoResponse(response)

        token_object.last_packet_unix = int(time.time())
        print("unix stamp updated")

        # packets recieve
        raw_bytes = KorchoBuffer(None)
        await raw_bytes.write_to_buffer(await request.body())

        response = bytearray()
        while not raw_bytes.EOF():
            packet_id = await raw_bytes.read_u_int_16()
            _ = await raw_bytes.read_int_8()  # empty byte
            packet_length = await raw_bytes.read_int_32()

            if packet_id == OsuPacketID.Client_Pong.value:
                # client just spamming it and tries to say, that he is normal :sip:
                continue

            data = await raw_bytes.slice_buffer(packet_length)

            if token_object.is_restricted and packet_id not in ALLOWED_RESTRICT_PACKETS:
                logger.wlog(f"[{token_object.token}/{token_object.name}] Ignored packet {packet_id}(account restrict)")
                continue

            if packet_id in OsuEvent.handlers:
                # This packet can be handled by OsuEvent Class, call it now!
                # Oh wait let go this thing in async executor.
                await OsuEvent.handlers[packet_id](data, token_object)
                logger.klog(
                    f"[{token_object.token}/{token_object.name}] Has triggered {packet_id} with packet length: {packet_length}")
            else:
                logger.wlog(f"[Events] Packet ID: {packet_id} not found in events handlers")

        while not token_object.is_queue_empty:
            response += token_object.dequeue()

        response = BanchoResponse(bytes(response), token=token_object.token)
        return response
    else:
        # first login
        # Structure (new line = "|", already split)
        # [0] osu! version
        # [1] plain mac addressed, separated by "."
        # [2] mac addresses hash set
        # [3] unique ID
        # [4] disk ID
        start_time = time.time()  # auth speed benchmark time

        loginData = (await request.body()).decode().split("\n")
        if len(loginData) < 3:
            return BanchoResponse(await PacketBuilder.UserID(-5))

        if not await userHelper.check_login(loginData[0], loginData[1], request.client.host):
            logger.elog(f"[{loginData[0]}] tried to login but failed with password")
            return BanchoResponse(await PacketBuilder.UserID(-1))

        user_data = await userHelper.get_start_user(loginData[0])
        if not user_data:
            return BanchoResponse(await PacketBuilder.UserID(-1))

        data = loginData[2].split("|")
        hashes = data[3].split(":")
        time_offset = int(data[1])
        pm_private = data[4] == '1'

        isTourney = "tourney" in data[0]

        # check if user already on kuriso
        if Context.players.get_token(uid=user_data['id']) and not isTourney:
            # wtf osu
            await Context.players.get_token(uid=user_data['id']).logout()

        if not (user_data["privileges"] & 3) and \
                (user_data["privileges"] & Privileges.USER_PENDING_VERIFICATION) == 0:
            logger.elog(f"[{loginData}] Banned chmo tried to login")
            response = (await PacketBuilder.UserID(-3) +
                        await PacketBuilder.Notification(
                            'You are banned. Join our discord for additional information.'))

            return BanchoResponse(bytes(response))
        if (user_data["privileges"] & Privileges.USER_PUBLIC) and \
                (user_data["privileges"] & Privileges.USER_NORMAL) == 0 and \
                (user_data["privileges"] & Privileges.USER_PENDING_VERIFICATION) == 0:
            logger.elog(f"[{loginData}] Locked dude tried to login")
            response = (await PacketBuilder.UserID(-1) +
                        await PacketBuilder.Notification(
                            'You are locked by staff. Join discord and ask for unlock!'))

            return BanchoResponse(bytes(response))

        if bool(Context.bancho_settings['bancho_maintenance']):
            # send to user that maintenance
            if not (user_data['privileges'] & KurikkuPrivileges.Developer):
                response = (await PacketBuilder.UserID(-1) +
                            await PacketBuilder.Notification(
                                'Kuriso! is in maintenance mode. Please try to login again later.'))

                return BanchoResponse(bytes(response))

        await Context.mysql.execute('''
            INSERT INTO hw_user (userid, mac, unique_id, disk_id, occurencies) VALUES (%s, %s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE occurencies = occurencies + 1''',
                                    [user_data['id'], hashes[2], hashes[3], hashes[4]]
                                    )  # log hardware и не ебёт что

        if (user_data['privileges'] & Privileges.USER_PENDING_VERIFICATION) or \
                not await userHelper.user_have_hardware(user_data['id']):
            # we need to verify our user
            is_success_verify = await userHelper.activate_user(user_data['id'], user_data['username'], hashes)
            if not is_success_verify:
                response = (await PacketBuilder.UserID(-1) +
                            await PacketBuilder.Notification(
                                'Your HWID is not clear. Contact Staff to create account!'))
                return BanchoResponse(bytes(response))
            else:
                await Context.mysql.execute(
                    "UPDATE hw_user SET activated = 1 WHERE userid = %s AND mac = %s AND unique_id = %s AND disk_id = %s",
                    [user_data['id'], hashes[2], hashes[3], hashes[4]]
                )

        osu_version = data[0]
        await userHelper.setUserLastOsuVer(user_data['id'], osu_version)
        osuVersionInt = osu_version[1:9]

        now = datetime.datetime.now()
        vernow = datetime.datetime(int(osuVersionInt[:4]), int(osuVersionInt[4:6]), int(osuVersionInt[6:8]), 00, 00)
        deltanow = now - vernow

        if not osuVersionInt[0].isdigit() or \
                deltanow.days > 360 or int(osuVersionInt) < 20200811:
            response = (await PacketBuilder.UserID(-2) +
                        await PacketBuilder.Notification(
                            'Sorry, you use outdated/bad osu!version. Please update your game to join server'))
            return BanchoResponse(bytes(response))

        if isTourney:
            if Context.players.get_token(uid=user_data['id']):
                # manager was logged before, we need just add additional token
                token, player = Context.players.get_token(uid=user_data['id']).add_additional_client()
            else:
                player = TourneyPlayer(int(user_data['id']), user_data['username'], user_data['privileges'],
                                       time_offset, pm_private,
                                       0 if user_data['silence_end'] - int(time.time()) < 0 else user_data['silence_end'] - int(
                                           time.time()), is_tourneymode=True, ip=request.client.host)
                await asyncio.gather(*[
                    player.parse_friends(),
                    player.update_stats(),
                    player.parse_country(request.client.host)
                ])
        else:
            # create Player instance finally!!!!
            player = Player(int(user_data['id']), user_data['username'], user_data['privileges'],
                            time_offset, pm_private,
                            0 if user_data['silence_end'] - int(time.time()) < 0 else user_data['silence_end'] - int(
                                time.time()), ip=request.client.host
                            )

            await asyncio.gather(*[
                player.parse_friends(),
                player.update_stats(),
                player.parse_country(request.client.host)
            ])

        start_bytes_async = await asyncio.gather(*[
            PacketBuilder.UserID(player.id),
            PacketBuilder.ProtocolVersion(19),
            PacketBuilder.BanchoPrivileges(player.bancho_privs),
            PacketBuilder.UserPresence(player),
            PacketBuilder.UserStats(player),
            PacketBuilder.FriendList(player.friends),
            PacketBuilder.SilenceEnd(player.silence_end if player.silence_end > 0 else 0),
            PacketBuilder.Notification(
                f'''Welcome to kuriso!\nBuild ver: v{Context.version}\nCommit: {Context.commit_id}'''),
            PacketBuilder.Notification(
                f'Authorization took: {round(time.time() - start_time, 4)}ms')
        ])
        start_bytes = b''.join(start_bytes_async)

        if bool(Context.bancho_settings['bancho_maintenance']):
            start_bytes += await PacketBuilder.Notification(
                'Don\'t forget enable server after maintenance :sip:')

        if Context.bancho_settings['menu_icon']:
            start_bytes += await PacketBuilder.MainMenuIcon(Context.bancho_settings['menu_icon'])

        if isTourney and Context.players.get_token(uid=user_data['id']):
            logger.klog(f"[{player.token}/{player.name}] Joined kuriso as additional client for origin!")
            for p in Context.players.get_all_tokens():
                if p.is_restricted:
                    continue

                start_bytes += bytes(
                    await PacketBuilder.UserPresence(p) +
                    await PacketBuilder.UserStats(p)
                )
        else:
            for p in Context.players.get_all_tokens():
                if p.is_restricted:
                    continue

                start_bytes += bytes(
                    await PacketBuilder.UserPresence(p) +
                    await PacketBuilder.UserStats(p)
                )
                p.enqueue(bytes(
                    await PacketBuilder.UserPresence(player) +
                    await PacketBuilder.UserStats(player)
                ))

            await userHelper.saveBanchoSession(player.id, request.client.host)

            Context.players.add_token(player)
            logger.klog(f"[{player.token}/{player.name}] Joined kuriso!")

        # default channels to join is #osu, #announce and #english
        await asyncio.gather(*[
            Context.channels['#osu'].join_channel(player),
            Context.channels['#announce'].join_channel(player),
            Context.channels['#english'].join_channel(player)
        ])

        for (_, chan) in Context.channels.items():
            if not chan.temp_channel and chan.can_read:
                start_bytes += await PacketBuilder.ChannelAvailable(chan)

        start_bytes += await PacketBuilder.ChannelListeningEnd()

        if player.is_restricted:
            start_bytes += await PacketBuilder.UserRestricted()
            await CrystalBot.ez_message(
                player.safe_name,
                "Your account is currently in restricted mode. Please visit kurikku's website for more information."
            )

        return BanchoResponse(start_bytes, player.token)
