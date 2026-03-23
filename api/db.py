import asyncpg
from fastapi import Request


class DBConnection:
    def __init__(self, postgres_dsn: str):
        self.postgres_dsn = postgres_dsn
        self.pool = None

    async def connect(self):
        if self.pool:
            return
        self.pool = await asyncpg.create_pool(self.postgres_dsn)

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def fetch(self, query: str, *args):
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)


async def get_db(request: Request) -> DBConnection:
    return request.app.state.db
