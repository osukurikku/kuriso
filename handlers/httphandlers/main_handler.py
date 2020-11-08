import hashlib
import time

from lib import logger
from starlette.requests import Request
from starlette.responses import HTMLResponse

from handlers.decorators import HttpEvent, OsuEvent
from lib.BanchoResponse import BanchoResponse
from blob import BlobContext
from objects import Privileges
from objects.KurikkuPrivileges import KurikkuPrivileges
from objects.Player import Player
from packets.builder.index import PacketBuilder
from packets.OsuPacketID import OsuPacketID
from packets.Reader.OsuTypes import osuTypes
from packets.Reader.index import CreateBanchoPacket, KorchoBuffer
from helpers import userHelper



@HttpEvent.register_handler("/", methods=['GET', 'POST'])
async def main_handler(request: Request):
    if request.headers.get("user-agent", "") != "osu!":
        return HTMLResponse("<html><h1>HEY BRO NICE DICK</h1></html>")

    token = request.headers.get("osu-token", None)
    if token:
        if token not in BlobContext.players or token == '':
            return BanchoResponse(await PacketBuilder.UserID(-1))  # send to re-login

        token_object = BlobContext.players.get(token, None)
        if not token_object:
            # is this even possible?
            return BanchoResponse(await PacketBuilder.UserID(-5))

        # packets recieve
        raw_bytes = KorchoBuffer(None)
        await raw_bytes.write_to_buffer(await request.body())

        response = bytearray()
        tasks = []
        while not raw_bytes.EOF():
            packet_id = await raw_bytes.read_u_int_16()
            _ = await raw_bytes.read_int_8()  # empty byte
            packet_length = await raw_bytes.read_int_32()

            if packet_id == OsuPacketID.Client_Pong.value:
                # client just spamming it and tries to say, that he is normal :sip:
                continue

            data = await raw_bytes.slice_buffer(packet_length)
            if packet_id in OsuEvent.handlers:
                # This packet can be handled by OsuEvent Class, call it now!
                # Oh wait let go this thing in async executor.
                await OsuEvent.handlers[packet_id](data, token_object)
                logger.klog(f"[{token_object.token}] Has triggered {packet_id} with packet length: {packet_length}")
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

        loginData = (await request.body()).decode().split("\n")
        if len(loginData) < 3:
            return BanchoResponse(await PacketBuilder.UserID(-1))

        if not await userHelper.check_login(loginData[0], loginData[1], request.client.host):
            logger.elog(f"[{loginData}] tried to login but failed with password")
            return BanchoResponse(await PacketBuilder.UserID(-1))

        user_data = await userHelper.get_start_user(loginData[0])
        if not user_data:
            return BanchoResponse(await PacketBuilder.UserID(-1))

        if not (user_data["privileges"] & 3 > 0) and \
                user_data["privileges"] & Privileges.USER_PENDING_VERIFICATION == 0:
            logger.elog(f"[{loginData}] Restricted chmo tried to login")
            response = await PacketBuilder.UserID(-3) + \
                       await PacketBuilder.Notification(
                           'You are restricted/banned. Join our discord for additional information.')

            return BanchoResponse(bytes(response))
        if (user_data["privileges"] & Privileges.USER_PUBLIC > 0) and \
                user_data["privileges"] & Privileges.USER_NORMAL == 0 and \
                user_data["privileges"] & Privileges.USER_PENDING_VERIFICATION == 0:
            logger.elog(f"[{loginData}] Locked dude tried to login")
            response = await PacketBuilder.UserID(-1) + \
                       await PacketBuilder.Notification(
                           'You are locked by staff. Join discord and ask for unlock!')

            return BanchoResponse(bytes(response))

        if bool(BlobContext.bancho_settings['bancho_maintenance']):
            # send to user that maintenance
            if not (user_data['privileges'] & KurikkuPrivileges.Developer):
                response = await PacketBuilder.UserID(-1) + \
                           await PacketBuilder.Notification(
                               'Kuriso! is in maintenance mode. Please try to login again later.')

                return BanchoResponse(bytes(response))

        data = loginData[2].split("|")
        hashes = data[3].split(":")
        time_offset = int(data[1])
        pm_private = data[4] == '1'

        await BlobContext.mysql.execute('''
            INSERT INTO hw_user (userid, mac, unique_id, disk_id, occurencies) VALUES (%s, %s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE occurencies = occurencies + 1''',
                                        [user_data['id'], hashes[2], hashes[3], hashes[4]]
                                        )  # log hardware и не ебёт что

        if user_data['privileges'] & Privileges.USER_PENDING_VERIFICATION > 0 or \
                not await userHelper.user_have_hardware(user_data['id']):
            # we need to verify our user
            is_success_verify = await userHelper.activate_user(user_data['id'], user_data['username'], hashes)
            if not is_success_verify:
                response = await PacketBuilder.UserID(-1) + \
                           await PacketBuilder.Notification(
                               'Your HWID is not clear. Contact Staff to create account!')
                return BanchoResponse(bytes(response))
            else:
                await BlobContext.mysql.execute(
                    "UPDATE hw_user SET activated = 1 WHERE userid = %s AND mac = %s AND unique_id = %s AND disk_id = %s",
                    [user_data['id'], hashes[2], hashes[3], hashes[4]]
                )

        # create Player instance finally!!!!
        player = Player(user_data['id'], user_data['username'], user_data['privileges'],
                        time_offset, pm_private,
                        0 if user_data['silence_end'] - int(time.time()) < 0 else user_data['silence_end'] - int(
                            time.time())
                        )

        await player.parse_friends()
        await player.update_stats()
        await player.parse_country(request.client.host)

        start_bytes = bytes(
            await PacketBuilder.UserID(player.id) +
            await PacketBuilder.ProtocolVersion(19) +
            await PacketBuilder.BanchoPrivileges(player.bancho_privs) +
            await PacketBuilder.UserPresence(player) +
            await PacketBuilder.UserStats(player) +
            await PacketBuilder.FriendList(player.friends) +
            await PacketBuilder.SilenceEnd(player.silence_end) +
            await PacketBuilder.Notification(f'''Welcome to kuriso!\nBuild ver: v{BlobContext.version}\nCommit: {BlobContext.commit_id}''')
        )

        if bool(BlobContext.bancho_settings['bancho_maintenance']):
            start_bytes += await PacketBuilder.Notification(
                               'Don\'t forget enable server after maintenance :sip:')

        if BlobContext.bancho_settings['menu_icon']:
            start_bytes += await PacketBuilder.MainMenuIcon(BlobContext.bancho_settings['menu_icon'])

        for p in BlobContext.players:
            start_bytes += bytes(
                await PacketBuilder.UserPresence(p) +
                await PacketBuilder.UserStats(p)
            )

        start_bytes += await CreateBanchoPacket(64, ("#osu", osuTypes.string)) # Empty channel, because i haven't channels right now
        # 64 - is channels which i should join
        # 65 - is available channels for channel list
        # await CreateBanchoPacket(96, ([999, 1000], osuTypes.i32_list))
        # await CreateBanchoPacket(89)
        # await CreateBanchoPacket(65, ("#ebat_public", osuTypes.string), ("Welcome to the cum!zone", osuTypes.string), (2, osuTypes.int32))

        # await CreateBanchoPacket(89) # send end channel
        BlobContext.players[player.token] = player

        return BanchoResponse(start_bytes, player.token)
