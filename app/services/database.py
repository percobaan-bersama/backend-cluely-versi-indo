import json
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

postgres_pool: asyncpg.Pool | None = None


def _get_database_url() -> str | None:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    db_host = os.getenv("DB_HOST", "127.0.0.1")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "cluely")
    db_user = os.getenv("DB_USER", "password")
    db_password = os.getenv("DB_PASSWORD", "password")

    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


async def initialize_database():
    global postgres_pool

    database_url = _get_database_url()
    if not database_url or postgres_pool is not None:
        return

    async def init(conn):
        await conn.set_type_codec(
            'jsonb',
            encoder=json.dumps,
            decoder=json.loads,
            schema='pg_catalog'
        )

    try:
        postgres_pool = await asyncpg.create_pool(
            dsn=database_url,
            init=init,
            min_size=1,
            max_size=5,
        )
        async with postgres_pool.acquire() as conn:
            # Prevent concurrent workers from racing on first-time schema setup.
            await conn.execute("SELECT pg_advisory_lock(424242)")
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    history JSONB NOT NULL DEFAULT '[]'::jsonb,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            await conn.execute("SELECT pg_advisory_unlock(424242)")
    except Exception as e:
        print(f"Error initializing PostgreSQL: {e}")
        postgres_pool = None


async def close_database():
    global postgres_pool

    if postgres_pool is not None:
        await postgres_pool.close()
        postgres_pool = None


async def get_session_history(session_id: str) -> list[dict]:
    if postgres_pool is None:
        return []

    try:
        async with postgres_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT history FROM chat_sessions WHERE session_id = $1",
                session_id,
            )
            if row and row["history"]:
                history = row["history"]
                return history if isinstance(history, list) else []
    except Exception as e:
        print(f"Error fetching session history from PostgreSQL: {e}")

    return []


async def save_session_history(session_id: str, history: list[dict]):
    if postgres_pool is None:
        return

    try:
        async with postgres_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO chat_sessions (session_id, history, updated_at)
                VALUES ($1, $2::jsonb, NOW())
                ON CONFLICT (session_id) DO UPDATE
                SET history = EXCLUDED.history,
                    updated_at = NOW()
                """,
                session_id,
                history,
            )
    except Exception as e:
        print(f"Error saving session history to PostgreSQL: {e}")


async def delete_session(session_id: str):
    if postgres_pool is None:
        return

    try:
        async with postgres_pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM chat_sessions WHERE session_id = $1",
                session_id,
            )
    except Exception as e:
        print(f"Error deleting session from PostgreSQL: {e}")
