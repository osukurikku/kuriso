import asyncio
import asyncio_redis
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import loops
import registrator
from starlette.applications import Starlette

import uvicorn
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from config import Config
from blob import Context

from lib import AsyncSQLPoolWrapper
from lib import logger

import nest_asyncio  # fix asyncio loops

nest_asyncio.apply()


async def main():
    # create simple Starlette through uvicorn app
    app = Starlette(debug=True)
    app.add_middleware(ProxyHeadersMiddleware)

    # load version
    Context.load_version()
    logger.klog(f"Hey! Starting kuriso! v{Context.version} (commit-id: {Context.commit_id})")
    logger.printColored(open("kuriso.MOTD", mode="r", encoding="utf-8").read(), logger.YELLOW)

    # Load all events & handlers
    registrator.load_handlers(app)

    # Load configuration for our project
    Config.load_config()
    logger.slog("[Config] Loaded")

    # Create Redis connection :sip:
    logger.wlog("[Redis] Trying connection to Redis")
    main_loop = asyncio.get_event_loop()
    _, protocol = await main_loop.create_connection(asyncio_redis.RedisProtocol, Config.config['redis']['host'],
                                                    Config.config['redis']['port'])
    await protocol.auth(password=Config.config['redis']['password'])
    await protocol.select(Config.config['redis']['db'])
    Context.redis = protocol
    logger.slog("[Redis] Connection to Redis established! Well done!")

    logger.slog("[Redis] Removing old information about redis...")
    try:
        await Context.redis.set("ripple:online_users", '0')
        del_keys_lua = '''
local matches = redis.call('KEYS', ARGV[1])

local result = 0
for _,key in ipairs(matches) do
    result = result + redis.call('DEL', key)
end

return result 
'''
        script = await protocol.register_script(del_keys_lua)
        await script.run(keys=[], args=["peppy:sessions:*"])
        await script.run(keys=[], args=["peppy:*"])
    except Exception:
        logger.elog("[Redis] initiation data ruined... Check this!")

    logger.wlog("[MySQL] Making connection to MySQL Database...")
    mysql_pool = AsyncSQLPoolWrapper()
    await mysql_pool.connect(**{
        'host': Config.config['mysql']['host'],
        'user': Config.config['mysql']['user'],
        'password': Config.config['mysql']['password'],
        'port': Config.config['mysql']['port'],
        'db': Config.config['mysql']['database'],
        'loop': main_loop,
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

    Context.load_motd()

    logger.slog(f"[Uvicorn] HTTP server started at {Config.config['host']['address']}:{Config.config['host']['port']}")
    uvicorn.run(app, host=Config.config['host']['address'], port=Config.config['host']['port'], log_level=logging.WARNING)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
