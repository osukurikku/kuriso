import asyncio
import logging
import traceback
import aioredis

import prometheus_client
import sentry_sdk
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

from lib import AsyncSQLPoolWrapper
from lib import logger
from dotenv import load_dotenv, find_dotenv

import nest_asyncio  # fix asyncio loops

nest_asyncio.apply()


async def main():
    # load dotenv file
    load_dotenv(find_dotenv())

    # Load configuration for our project
    Config.load_config()
    logger.slog("[Config] Loaded")

    # create simple Starlette through uvicorn app
    app = Starlette(debug=Config.config['debug'])
    app.add_middleware(ProxyHeadersMiddleware)

    if Config.config['sentry']['enabled']:
        sentry_sdk.init(dsn=Config.config['sentry']['url'])
        app.add_middleware(SentryMiddleware)

    # load version
    Context.load_version()
    logger.klog(f"Hey! Starting kuriso! v{Context.version} (commit-id: {Context.commit_id})")
    logger.printColored(open("kuriso.MOTD", mode="r", encoding="utf-8").read(), logger.YELLOW)

    # Load all events & handlers
    registrator.load_handlers(app)

    # Create Redis connection :sip:
    logger.wlog("[Redis] Trying connection to Redis")

    redis_values = dict(
        db=Config.config['redis']['db'],
        minsize=5,
        maxsize=10
    )
    if Config.config['redis']['password']:
        redis_values['password'] = Config.config['redis']['password']
    
    redis_pool = await aioredis.create_redis_pool(
        f"redis://{Config.config['redis']['host']}",
        **redis_values
    )

    Context.redis = redis_pool
    logger.slog("[Redis] Connection to Redis established! Well done!")

    logger.slog("[Redis] Removing old information about redis...")
    try:
        await Context.redis.set("ripple:online_users", "0")
        redis_flush_script = '''
local matches = redis.call('KEYS', ARGV[1])

local result = 0
for _,key in ipairs(matches) do
    result = result + redis.call('DEL', key)
end

return result
'''
        await Context.redis.eval(redis_flush_script, args=["peppy:*"])
        await Context.redis.eval(redis_flush_script, args=["peppy:sessions:*"])
    except Exception as e:
        traceback.print_exc()
        capture_exception(e)
        logger.elog("[Redis] initiation data ruined... Check this!")

    await Context.redis.set("peppy:version", Context.version)

    logger.wlog("[MySQL] Making connection to MySQL Database...")
    mysql_pool = AsyncSQLPoolWrapper()
    await mysql_pool.connect(**{
        'host': Config.config['mysql']['host'],
        'user': Config.config['mysql']['user'],
        'password': Config.config['mysql']['password'],
        'port': Config.config['mysql']['port'],
        'db': Config.config['mysql']['database'],
        'loop': asyncio.get_event_loop(),
        'autocommit': True
    })
    Context.mysql = mysql_pool
    logger.slog("[MySQL] Connection established!")

    if Config.config['prometheus']['enabled']:
        logger.wlog("[Prometheus stats] Loading...")
        prometheus_client.start_http_server(
            Config.config['prometheus']['port'], 
            addr=Config.config['prometheus']['host']
        )
        logger.slog("[Prometheus stats] Metrics started...")

    # now load bancho settings
    await Context.load_bancho_settings()
    await registrator.load_default_channels()

    from bot.bot import CrystalBot
    # now load bot
    await CrystalBot.connect()
    # and register bot commands
    CrystalBot.load_commands()

    logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)

    scheduler = AsyncIOScheduler()
    scheduler.start()
    scheduler.add_job(loops.clean_timeouts, "interval", seconds=60)
    if Config.config['prometheus']['enabled']:
        scheduler.add_job(loops.add_prometheus_stats, "interval", seconds=15)
    scheduler.add_job(loops.add_stats, "interval", seconds=120)

    # Setup pub/sub listeners for LETS/old admin panel events
    event_loop = asyncio.get_event_loop()
    event_loop.create_task(pubsub_listeners.init())

    Context.load_motd()
    uvicorn.run(app, host=Config.config['host']['address'], port=Config.config['host']['port'], access_log=False)


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
            Context.redis.close()
            await Context.redis.wait_closed()

        # Stop redis sub connection
        logger.elog("[Server] Stopping redis subscriber pool...")
        if Context.redis_sub:
            Context.redis_sub.close()
            await Context.redis_sub.wait_closed()

        # Stop mysql pool connection
        logger.elog("[Server] Stopping mysql pool...")
        if Context.mysql:
            Context.mysql.pool.close()
            await Context.mysql.pool.wait_closed()

        logger.elog("[Server] Disposing uvicorn instance...")

    def _manager(*args, **kwargs):
        if Context.is_shutdown:
            return
        loop = asyncio.get_event_loop()
        Context.is_shutdown = True
        loop.run_until_complete(_shutdown())
        original_handler(*args, **kwargs)

    return _manager


orig_handle = Server.handle_exit
Server.handle_exit = shutdown(orig_handle)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
