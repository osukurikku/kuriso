import asyncio
import time

from blob import Context
from config import Config
from lib import logger

LAST_PACKET_TIMEOUT = 240


async def clean_timeouts():
    """
    loop, that cleans timeout users, because if dude ALT-F4 Client, it can have bad end
    """

    tasks = []
    for _, user in Context.players.store_by_token.items():
        if user.is_bot:
            continue  # ignore bot

        if hasattr(user, "additional_clients"):
            for _, sub_user in user.additional_clients.items():
                if int(time.time()) - sub_user.last_packet_unix > LAST_PACKET_TIMEOUT:
                    logger.slog(f"[Player/{user.name}/subclient] was kicked during timeout")
                    # simulate logout packet
                    tasks.append(sub_user.logout())

        if int(time.time()) - user.last_packet_unix > LAST_PACKET_TIMEOUT:
            logger.slog(f"[Player/{user.name}] was kicked during timeout")
            # simulate logout packet
            tasks.append(user.logout())

    await asyncio.gather(*tasks)


async def add_stats():
    if Config.config["stats_enabled"]:
        # start thread
        online_users = len(Context.players.get_all_tokens(ignore_tournament_clients=True))
        multiplayers_matches = len(Context.matches.items())

        await Context.mysql.execute(
            "INSERT INTO bancho_stats (users_osu, multiplayer_games) VALUES (:online_users, :multiplayer_matches)",
            {"online_users": online_users, "multiplayer_matches": multiplayers_matches},
        )


async def add_prometheus_stats():
    """
    That code calls every 15s!
    """
    online_users = len(Context.players.get_all_tokens(ignore_tournament_clients=True))
    multiplayers_matches = len(Context.matches.items())
    Context.stats["online_users"].set(online_users)
    Context.stats["multiplayer_matches"].set(multiplayers_matches)
