from typing import Optional, AsyncGenerator, Any, Dict

import aiomysql


class AsyncSQLPoolWrapper:
    __slots__ = ('pool',)

    def __init__(self):
        self.pool: Optional[aiomysql.Pool] = None

    async def connect(self, **config):
        self.pool = await aiomysql.create_pool(**config)

    async def execute(self, query: str, params=None) -> int:
        if params is None:
            params = []
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, params)
                await conn.commit()

                last_row_id = cur.lastrowid

        return last_row_id

    async def fetch(self, query: str, params=None,
                    _all: bool = False, _dict: bool = True
                    ) -> Optional[Dict[str, Any]]:
        if params is None:
            params = []
        cursor_type = aiomysql.DictCursor if _dict else aiomysql.Cursor

        async with self.pool.acquire() as conn:
            async with conn.cursor(cursor_type) as cur:
                await cur.execute(query, params)

                if _all:
                    res = await cur.fetchall()
                else:
                    res = await cur.fetchone()

        return res

    async def fetchall(self, query: str, params=None,
                       _dict: bool = True) -> Optional[Dict[str, Any]]:
        if params is None:
            params = []
        return await self.fetch(query, params, _all=True, _dict=_dict)

    async def iterall(self, query: str, params=None,
                      _dict: bool = True) -> AsyncGenerator[Optional[Dict[str, Any]], None]:
        if params is None:
            params = []
        cursor_type = aiomysql.DictCursor if _dict else aiomysql.Cursor

        async with self.pool.acquire() as conn:
            async with conn.cursor(cursor_type) as cur:
                await cur.execute(query, params)

                async for row in cur:
                    yield row
