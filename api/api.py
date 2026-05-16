from aiohttp import web
import logging
from datetime import datetime

# --- Route registration and CORS setup ---
def setup_admin_routes(app: web.Application):
    # Expose registration and retrieval endpoints under consistent namespaces
    app.router.add_post("/api/users/register", handle_user_registration)
    app.router.add_get("/api/users", list_users)

# --- Standard Request Handlers ---

async def handle_user_registration(request: web.Request):
    """
    Registers standard profile metadata for internal system access.
    """
    try:
        data = await request.json()
        email = data.get("email")
        display_name = data.get("display_name")

        if not email or not display_name:
            return web.json_response({"error": "Missing required profile fields"}, status=400)

        # Access database pool assigned during application configuration
        db = request.app.get('db')
        if not db:
            return web.json_response({"error": "Database context unavailable"}, status=500)

        # Safe parameter insertion for regular profiles
        user_id = await db.create_system_profile(email=email, display_name=display_name)

        return web.json_response({
            "status": "success",
            "user_id": user_id,
            "message": "System registration complete"
        }, status=200)

    except Exception as e:
        logging.exception("Registration pipeline processing error: %s", e)
        return web.json_response({"error": "Internal processing error"}, status=500)


async def list_users(request: web.Request):
    """
    Queries standard system metadata to return a high-performance scannable list.
    """
    try:
        db_pool = request.app.get('db_pool') # Ensure this matches your initialization setup
        if not db_pool:
            return web.json_response({"error": "Database connection pool uninitialized"}, status=500)

        # Simple analytical query on standard internal table structures
        sql = """
        SELECT id, email, display_name, is_active, created_at 
        FROM system_profiles 
        ORDER BY created_at DESC 
        LIMIT 500;
        """

        async with db_pool.acquire() as conn:
            rows = await conn.fetch(sql)
            
            records = []
            for r in rows:
                rec = dict(r)
                if isinstance(rec.get("created_at"), datetime):
                    rec["created_at"] = rec["created_at"].isoformat()
                records.append(rec)

        return web.json_response(records)

    except Exception as e:
        logging.exception("Failed to query application registries: %s", e)
        return web.json_response([], status=500)