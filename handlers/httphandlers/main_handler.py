import asyncio
import hashlib
import time

from lib import logger
from starlette.requests import Request
from starlette.responses import PlainTextResponse, HTMLResponse

from handlers.decorators import HttpEvent, OsuEvent
from objects import Privileges
from objects.Token import Token
from packets.OsuPacketID import OsuPacketID
from packets.Reader.OsuTypes import osuTypes
from packets.Reader.index import CreateBanchoPacket, KorchoBuffer
from helpers import userHelper
from blob import BlobContext
from packets.builder.index import PacketBuilder


@HttpEvent.register_handler("/", methods=['GET', 'POST'])
async def main_handler(request: Request):
    if request.headers.get("user-agent", "") != "osu!":
        return HTMLResponse("<html><h1>HEY BRO NICE DICK</h1></html>")

    token = request.headers.get("osu-token", None)
    if token:
        if token not in BlobContext.tokens:
            return HTMLResponse(await PacketBuilder.UserID(-1))  # send to re-login

        token_object = BlobContext.tokens.get(token, None)
        if not token_object:
            # is this even possible?
            return HTMLResponse(await PacketBuilder.UserID(-5))

        # packets recieve
        raw_bytes = KorchoBuffer(None)
        await raw_bytes.write_to_buffer(await request.body())

        response = bytearray()
        tasks = []
        while not raw_bytes.EOF():
            packet_id = await raw_bytes.read_u_int_16()
            _ = await raw_bytes.read_int_8()  # empty byte
            packet_length = await raw_bytes.read_int_32()

            if packet_id == OsuPacketID.Client_Pong:
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

        response = HTMLResponse(bytes(response))
        response.headers['cho-protocol'] = '19'
        response.headers['Server'] = 'bancho'
        response.headers['connection'] = 'Keep-Alive'
        response.headers['vary'] = 'Accept-Encoding'
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
            return HTMLResponse(await PacketBuilder.UserID(-1))

        if not await userHelper.check_login(loginData[0], loginData[1], request.client.host):
            logger.elog(f"[{loginData}] tried to login but failed with password")
            return HTMLResponse(await PacketBuilder.UserID(-1))

        user_data = await userHelper.get_start_user(loginData[0])
        if not user_data:
            return HTMLResponse(await PacketBuilder.UserID(-1))

        if not (user_data["privileges"] & 3 > 0) and \
                user_data["privileges"] & Privileges.USER_PENDING_VERIFICATION == 0:
            logger.elog(f"[{loginData}] Restricted chmo tried to login")
            response = await PacketBuilder.UserID(-1) + \
                       await PacketBuilder.Notification(
                           'You are restricted/banned. Join our discord for additional information.')

            return HTMLResponse(bytes(response))
        if (user_data["privileges"] & Privileges.USER_PUBLIC > 0) and \
                user_data["privileges"] & Privileges.USER_NORMAL == 0 and \
                user_data["privileges"] & Privileges.USER_PENDING_VERIFICATION == 0:
            logger.elog(f"[{loginData}] Locked dude tried to login")
            response = await PacketBuilder.UserID(-1) + \
                       await PacketBuilder.Notification(
                           'You are locked by staff. Join discord and ask for unlock!')

            return HTMLResponse(bytes(response))

        data = loginData[2].split("|")
        time_offset = int(data[1])

        dataBuffer = KorchoBuffer(None)
        # sending user-id
        start_packets = (
            await CreateBanchoPacket(75, (19, osuTypes.int32)),  # send 19 protocol version
            await CreateBanchoPacket(5, (1000, osuTypes.int32)),  # send 1000 user id
            await CreateBanchoPacket(83,
                                     (1000, osuTypes.int32),
                                     (loginData[0], osuTypes.string),
                                     (time_offset + 24, osuTypes.u_int8),
                                     (111, osuTypes.u_int8),
                                     (1 << 3, osuTypes.u_int8),
                                     (0.00, osuTypes.float32),
                                     (0.00, osuTypes.float32),
                                     (1, osuTypes.int32)
                                     ),  # send user presence
            await CreateBanchoPacket(72, ([999, 1001], osuTypes.i32_list)),  # friend list
            await CreateBanchoPacket(83,
                                     (999, osuTypes.int32),
                                     ("peppybot", osuTypes.string),
                                     (0 + 24, osuTypes.u_int8),
                                     (1, osuTypes.u_int8),
                                     (1 << 3, osuTypes.u_int8),
                                     (0.00, osuTypes.float32),
                                     (0.00, osuTypes.float32),
                                     (0, osuTypes.int32)
                                     ),  # send another presences
            await CreateBanchoPacket(11,
                                     (1000, osuTypes.int32),
                                     (0, osuTypes.u_int8),
                                     ("flexing on koncho", osuTypes.string),
                                     ("", osuTypes.string),
                                     (0, osuTypes.int32),  # mods
                                     (0, osuTypes.u_int8),  # playmode
                                     (0, osuTypes.int32),  # beatmap id
                                     (1, osuTypes.int64),  # ranked score
                                     (1, osuTypes.float32),  # accuracy
                                     (1, osuTypes.int32),  # total plays
                                     (1, osuTypes.int64),  # total score
                                     (1, osuTypes.int32),  # playmode rank
                                     (1, osuTypes.int16)  # pp
                                     ),  # send user stats
            await CreateBanchoPacket(71, (1 << 3, osuTypes.int32)),  # send owner privs (peppy)
            await CreateBanchoPacket(64, ("#osu", osuTypes.string)),
            await CreateBanchoPacket(92, (0, osuTypes.u_int32)),  # send end silence time

            await CreateBanchoPacket(11,
                                     (999, osuTypes.int32),
                                     (0, osuTypes.u_int8),
                                     ("flexing on peppy's island", osuTypes.string),
                                     ("", osuTypes.string),
                                     (0, osuTypes.int32),  # mods
                                     (0, osuTypes.u_int8),  # playmode
                                     (0, osuTypes.int32),  # beatmap id
                                     (1, osuTypes.int64),  # ranked score
                                     (1.00, osuTypes.float32),  # accuracy
                                     (1, osuTypes.int32),  # total plays
                                     (1, osuTypes.int64),  # total score
                                     (1, osuTypes.int32),  # playmode rank
                                     (1, osuTypes.int16)  # pp
                                     ),  # send bot stats

            await CreateBanchoPacket(24, ("Welcome to HUETA", osuTypes.string))  # send 1000 user id
        )
        for p in start_packets:
            print(p)
            await dataBuffer.write_to_buffer(p)

        # await CreateBanchoPacket(96, ([999, 1000], osuTypes.i32_list))
        # await CreateBanchoPacket(89)
        # await CreateBanchoPacket(65, ("#ebat_public", osuTypes.string), ("Welcome to the cum!zone", osuTypes.string), (2, osuTypes.int32))

        # await CreateBanchoPacket(89) # send end channel
        new_token = Token(hashlib.md5(f"{loginData[0]}:{loginData[1]}:{int(time.time())}".encode()).hexdigest())
        BlobContext.tokens[new_token.token] = new_token

        response = HTMLResponse(dataBuffer.get_string())
        print(new_token.token)
        response.headers['cho-token'] = new_token.token
        response.headers['cho-protocol'] = '19'
        response.headers['Server'] = 'bancho'
        response.headers['connection'] = 'Keep-Alive'
        response.headers['vary'] = 'Accept-Encoding'

        return response
