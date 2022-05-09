import asyncio
import logging
import sys
import traceback

import aioredis

import prometheus_client
import sentry_sdk
from databases import Database
from sentry_sdk import capture_exception
from sentry_asgi import SentryMiddleware

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import loops
import registrator
import pubsub_listeners

import uvicorn
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from uvicorn.main import Server
from starlette.applications import Starlette

from config import Config
from blob import Context
from irc import IRCStreamsServer

# from lib import AsyncSQLPoolWrapper
from lib import logger
from dotenv import load_dotenv, find_dotenv

from lib.asyncio_run import asyncio_run


async def main():
    # load dotenv file
    load_dotenv(find_dotenv())

    # Load configuration for our project
    Config.load_config()
    logger.slog("[Config] Loaded")

    # create simple Starlette through uvicorn app
    app = Starlette(debug=Config.config["debug"])
    app.add_middleware(ProxyHeadersMiddleware)

    if Config.config["sentry"]["enabled"]:
        sentry_sdk.init(
            dsn=Config.config["sentry"]["url"],
            environment="production" if not Config.config["debug"] else "development",
        )
        app.add_middleware(SentryMiddleware)

    # load version
    Context.load_version()
    logger.klog(f"Hey! Starting kuriso! v{Context.version} (commit-id: {Context.commit_id})")
    with open("kuriso.MOTD", encoding="utf-8") as kuriso_hello:
        logger.printColored(kuriso_hello.read(), logger.YELLOW)

    # Load all events & handlers
    registrator.load_handlers(app)

    # Create Redis connection :sip:
    logger.wlog("[Redis] Trying connection to Redis")

    redis_values = dict(
        db=Config.config["redis"]["db"],
        encoding="utf-8",
        decode_responses=True,
    )
    if Config.config["redis"]["password"]:
        redis_values["password"] = Config.config["redis"]["password"]

    redis_pool = await aioredis.from_url(
        f"redis://{Config.config['redis']['host']}", **redis_values
    )

    Context.redis = redis_pool
    logger.slog("[Redis] Connection to Redis established! Well done!")

    logger.slog("[Redis] Removing old information about redis...")
    try:
        await Context.redis.set("ripple:online_users", "0")
        redis_flush_script = """
local matches = redis.call('KEYS', ARGV[1])

local result = 0
for _,key in ipairs(matches) do
    result = result + redis.call('DEL', key)
end

return result
"""
        await Context.redis.eval(redis_flush_script, 1, *"peppy:*")
        await Context.redis.eval(redis_flush_script, 1, *"peppy:sessions:*")
    except Exception as e:
        traceback.print_exc()
        capture_exception(e)
        logger.elog("[Redis] initiation data ruined... Check this!")

    await Context.redis.set("peppy:version", Context.version)

    logger.wlog("[MySQL] Making connection to MySQL Database...")
    mysql_pool = Database(
        f"mysql://{Config.config['mysql']['user']}:{Config.config['mysql']['password']}@{Config.config['mysql']['host']}:{Config.config['mysql']['port']}/{Config.config['mysql']['database']}?charset=utf-8",
    )
    await mysql_pool.connect()
    Context.mysql = mysql_pool
    logger.slog("[MySQL] Connection established!")

    if Config.config["prometheus"]["enabled"]:
        logger.wlog("[Prometheus stats] Loading...")
        prometheus_client.start_http_server(
            Config.config["prometheus"]["port"],
            addr=Config.config["prometheus"]["host"],
        )
        logger.slog("[Prometheus stats] Metrics started...")

    logger.wlog("[Local GeoIP2] Trying to load local geoip database")
    if not Context.try_to_load_geoip2():
        logger.elog("[Local GeoIP2] Can't locate local file. Using environment variable...")
    else:
        logger.slog("[Local GeoIP2] Loaded successfully")

    # now load bancho settings
    await Context.load_bancho_settings()
    await registrator.load_default_channels()

    # pylint: disable=import-outside-toplevel
    from bot.bot import CrystalBot

    # now load bot
    await CrystalBot.connect()
    # and register bot commands
    CrystalBot.load_commands()

    logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)

    scheduler = AsyncIOScheduler()
    scheduler.start()
    scheduler.add_job(loops.clean_timeouts, "interval", seconds=60)
    if Config.config["prometheus"]["enabled"]:
        scheduler.add_job(loops.add_prometheus_stats, "interval", seconds=15)
    scheduler.add_job(loops.add_stats, "interval", seconds=120)

    # Setup pub/sub listeners for LETS/old admin panel events
    asyncio_run(pubsub_listeners.init())
    asyncio_run(asyncio.start_server(IRCStreamsServer, "127.0.0.1", 6667))

    Context.load_motd()
    uvicorn.run(
        app,
        host=Config.config["host"]["address"],
        port=Config.config["host"]["port"],
        access_log=False,
    )


def shutdown(original_handler):
    async def _shutdown():
        logger.elog("[System] Disposing server!")
        logger.elog("[System] Disposing players!")
        for player in Context.players.get_all_tokens():
            await player.say_bancho_restarting()

        logger.elog("[Server] Awaiting when players will get them packets!")
        attempts = 0
        while any(len(x.queue) > 0 for x in Context.players.get_all_tokens()):
            await asyncio.sleep(5)
            attempts += 1
            logger.elog(f"[Server] Attempt {attempts}/3")
            if attempts == 3:
                break

        # Stop redis connection
        logger.elog("[Server] Stopping redis pool...")
        if Context.redis:
            await Context.redis.close()

        # Stop mysql pool connection
        logger.elog("[Server] Stopping mysql pool...")
        if Context.mysql:
            await Context.mysql.disconnect()

        logger.elog("[Server] Disposing uvicorn instance...")

    def _manager(*args, **kwargs):
        if Context.is_shutdown:
            return

        Context.is_shutdown = True
        asyncio_run(_shutdown())
        original_handler(*args, **kwargs)
        sys.exit(0)

    return _manager


orig_handle = Server.handle_exit
Server.handle_exit = shutdown(orig_handle)

if __name__ == "__main__":
    asyncio_run(main())
