import asyncpg
import logging
from typing import Optional, Any, Dict
from datetime import datetime

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

CREATE TABLE IF NOT EXISTS admin_settings (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
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
    
    
    async def disconnect(self):
        if self._pool:
            await self._pool.close()# Database connection and SCHEMA_SQL

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
        
    

    from datetime import datetime

    async def fetch_users(self):
        query = """
        SELECT id, email, password, is_active, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT 500;
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query)

            result = []
            for r in rows:
                row = dict(r)

                if isinstance(row.get("created_at"), datetime):
                    row["created_at"] = row["created_at"].isoformat()

                result.append(row)

            return result
        
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
        
    
        

    async def verify_admin(self, username, password):
        query = """
        SELECT username, password
        FROM admin_settings
        WHERE username = $1;
        """

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, username)

            if not row:
                return False

            return row["password"] == password
        


    async def update_admin_password(self, username, new_password):
        query = """
        UPDATE admin_settings
        SET password = $1,
            updated_at = NOW()
        WHERE username = $2;
        """

        async with self._pool.acquire() as conn:
            await conn.execute(query, new_password, username)
            