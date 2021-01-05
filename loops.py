import asyncio
import time

from blob import Context
from lib import logger

LAST_PACKET_TIMEOUT = 20


async def clean_timeouts():
    '''
        loop, that cleans timeout users, because if dude ALT-F4 Client, it can have bad end
    '''

    tasks = []
    for (id, user) in Context.players.store_by_token.items():
        if user.is_bot:
            continue  # ignore bot

        if hasattr(user, "additional_clients"):
            for (_, sub_user) in user.additional_clients.items():
                if int(time.time()) - sub_user.last_packet_unix > LAST_PACKET_TIMEOUT:
                    logger.slog(f"[Player/{user.name}/subclient] was kicked during timeout")
                    # simulate logout packet
                    tasks.append(sub_user.logout())

        if int(time.time()) - user.last_packet_unix > LAST_PACKET_TIMEOUT:
            logger.slog(f"[Player/{user.name}] was kicked during timeout")
            # simulate logout packet
            tasks.append(user.logout())

    await asyncio.gather(*tasks)
