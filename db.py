import asyncpg
import logging
from typing import Optional, Any, Dict

SCHEMA_SQL = """
-- 1. Users Table (Optimized for simple credentials storage)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password TEXT NOT NULL, -- Stores plain-text password
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Optimization Index for rapid login/lookup requests
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
"""

class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        if not self._pool:
            self._pool = await asyncpg.create_pool(
                self.dsn,
                min_size=1,
                max_size=10,
                statement_cache_size=0
            )
            logging.info("Connected to PostgreSQL User Database")

    async def setup(self):
        async with self._pool.acquire() as conn:
            await conn.execute(SCHEMA_SQL)

    # --- USER METHODS ---
    
    async def create_user(self, email: str, password: str) -> Optional[int]:
        """
        Inserts a new user with an email and plain-text password.
        Returns the user ID, or None if the email already exists.
        """
        query = """
        INSERT INTO users (email, password) 
        VALUES ($1, $2) 
        ON CONFLICT (email) DO NOTHING
        RETURNING id;
        """
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, email.lower().strip(), password)

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a user record by email for authentication verification.
        """
        query = """
        SELECT id, email, password, is_active 
        FROM users 
        WHERE email = $1;
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, email.lower().strip())
            return dict(row) if row else None