import asyncio
import time

from blob import Context

LAST_PACKET_TIMEOUT = 20


async def clean_timeouts():
    '''
        loop, that cleans timeout users, because if dude ALT-F4 Client, it can have bad end
    '''

    print("loop? it needed?!")
    while True:
        print("Timeout checked")
        for (id, user) in Context.players.store_by_token.items():
            if hasattr(user, "additional_clients"):
                for (_, sub_user) in user.additional_clients.items():
                    if int(time.time()) - sub_user.last_packet_unix > LAST_PACKET_TIMEOUT:
                        print(user.id, "subclient get ready for kick")
                        # simulate logout packet
                        await sub_user.logout()

            if int(time.time()) - user.last_packet_unix > LAST_PACKET_TIMEOUT:
                print(user.id, "get ready for kick")
                # simulate logout packet
                await user.logout()

            # if hasattr(user, "additional_clients"):
            #     # check timeout on sub clients

        await asyncio.sleep(60)
        print("crashed? to next")

    print("loop?")
