import aiomysql
import os
import asyncio

class DatabaseManager:
    def __init__(self):
        self.pool = None

    async def connect(self):
        db_name = os.getenv("MYSQLDATABASE", "bot_db")
        host = os.getenv("MYSQLHOST", "127.0.0.1")
        port = int(os.getenv("MYSQLPORT", 3306))
        user = os.getenv("MYSQLUSER", "root")
        password = os.getenv("MYSQLPASSWORD", "")

        try:
            # Ensure database exists
            conn = await aiomysql.connect(
                host=host, port=port, user=user, password=password
            )
            async with conn.cursor() as cur:
                await cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.close()

            # Create pool
            self.pool = await aiomysql.create_pool(
                host=host, port=port, user=user, password=password,
                db=db_name, autocommit=True, minsize=1, maxsize=10
            )
            print(f"✅ Database connected: {db_name}")
            return self.pool
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            raise

    async def close(self):
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()

    async def execute(self, query, *params):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                return cur

    async def fetchone(self, query, *params):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                return await cur.fetchone()

    async def fetchall(self, query, *params):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                return await cur.fetchall()

    async def init_tables(self, tables):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                for table in tables:
                    try:
                        await cur.execute(table)
                    except Exception as e:
                        print(f"⚠️ Error creating table: {e}")
