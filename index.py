import logging
from concurrent.futures.process import ProcessPoolExecutor

import asyncio_redis
from starlette.applications import Starlette
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
import registrator
from lib import logger
import uvicorn
import asyncio
from config import Config
from blob import BlobContext
import nest_asyncio
# fix asyncio loops
from lib import AsyncSQLPoolWrapper

nest_asyncio.apply()


async def main():
    # create simple Starlette through uvicorn app
    app = Starlette(debug=True)
    app.add_middleware(ProxyHeadersMiddleware)

    # say goodbye to info logging by uvicorn
    logging.getLogger("uvicorn").setLevel(logging.WARNING)

    # Load all events & handlers
    registrator.load_handlers(app)

    # Load configuration for our project
    Config.load_config()
    logger.slog("[Config] Loaded")

    logger.wlog("[Redis] Trying connection to Redis")
    # Create Redis connection :sip:
    loop = asyncio.get_event_loop()
    transport, protocol = await loop.create_connection(asyncio_redis.RedisProtocol, Config.config['redis']['host'],
                                                       Config.config['redis']['port'])
    await protocol.auth(password=Config.config['redis']['password'])
    await protocol.select(Config.config['redis']['db'])
    BlobContext.redis = protocol
    logger.slog("[Redis] Connection to Redis established! Done well!")

    logger.wlog("[MySQL] Making connection to MySQL Database...")
    mysql_pool = AsyncSQLPoolWrapper()
    await mysql_pool.connect(**{
        'host': Config.config['mysql']['host'],
        'user': Config.config['mysql']['user'],
        'password': Config.config['mysql']['password'],
        'port': Config.config['mysql']['port'],
        'db': Config.config['mysql']['database'],
        'loop': loop,
    })
    BlobContext.mysql = mysql_pool
    logger.slog("[MySQL] Connection established!")

    logger.slog(f"[Uvicorn] HTTP server started at {Config.config['host']['address']}:{Config.config['host']['port']}")
    uvicorn.run(app, host=Config.config['host']['address'], port=Config.config['host']['port'],
                log_level=logging.WARNING)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
