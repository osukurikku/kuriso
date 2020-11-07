'''
This file contains context features :sip:
'''
from typing import Union

from lib import AsyncSQLPoolWrapper
import asyncio_redis


class BlobContext:
    """Singleton конфигурация"""
    tokens: Union[dict] = {}
    channels = [] # TODO: Union with channels
    matches = [] # TODO: Union with matches

    mysql: AsyncSQLPoolWrapper = None
    redis: asyncio_redis.RedisProtocol = None

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(BlobContext, cls).__new__(cls)
        return cls.instance
