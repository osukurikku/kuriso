import asyncio
import logging
import traceback

import aioredis

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import loops
import registrator
import pubsub_listeners
from starlette.applications import Starlette

import uvicorn
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

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

    # load version
    Context.load_version()
    logger.klog(f"Hey! Starting kuriso! v{Context.version} (commit-id: {Context.commit_id})")
    logger.printColored(open("kuriso.MOTD", mode="r", encoding="utf-8").read(), logger.YELLOW)

    # Load all events & handlers
    registrator.load_handlers(app)

    # Create Redis connection :sip:
    logger.wlog("[Redis] Trying connection to Redis")
    redis_pool = await aioredis.create_redis_pool(
        f"redis://{Config.config['redis']['host']}",
        password=Config.config['redis']['password'], db=Config.config['redis']['db'],
        minsize=5, maxsize=10)

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
    except Exception:
        traceback.print_exc()
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
    })
    Context.mysql = mysql_pool
    logger.slog("[MySQL] Connection established!")

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
    scheduler.add_job(loops.add_stats, "interval", seconds=120)

    # Setup pub/sub listeners for LETS/old admin panel events
    event_loop = asyncio.get_event_loop()
    event_loop.create_task(pubsub_listeners.init())

    Context.load_motd()
    uvicorn.run(app, host=Config.config['host']['address'], port=Config.config['host']['port'], access_log=False)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
