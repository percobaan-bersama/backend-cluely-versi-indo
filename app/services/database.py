import json
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
postgres_pool: asyncpg.Pool | None = None


async def initialize_database():
    global postgres_pool

    if not DATABASE_URL or postgres_pool is not None:
        return

    try:
        postgres_pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            min_size=1,
            max_size=5,
        )
        async with postgres_pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    history JSONB NOT NULL DEFAULT '[]'::jsonb,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
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
                return row["history"]
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
                json.dumps(history),
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
