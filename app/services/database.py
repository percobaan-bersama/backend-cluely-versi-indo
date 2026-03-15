import os
from supabase import create_client, Client
from dotenv import load_dotenv
import json

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

supabase: Client = None

if url and key and url != "your-supabase-url-here":
    try:
        supabase = create_client(url, key)
    except Exception as e:
        print(f"Error initializing Supabase: {e}")

async def get_session_history(session_id: str) -> list[dict]:
    if not supabase:
        return []
    
    try:
        response = supabase.table("chat_sessions").select("history").eq("session_id", session_id).execute()
        if response.data:
            return response.data[0].get("history", [])
    except Exception as e:
        print(f"Error fetching session history: {e}")
    
    return []

async def save_session_history(session_id: str, history: list[dict]):
    if not supabase:
        return
    
    try:
        data = {
            "session_id": session_id,
            "history": history,
            "updated_at": "now()"
        }
        
        supabase.table("chat_sessions").upsert(data).execute()
    except Exception as e:
        print(f"Error saving session history: {e}")

async def delete_session(session_id: str):
    if not supabase:
        return
    
    try:
        supabase.table("chat_sessions").delete().eq("session_id", session_id).execute()
    except Exception as e:
        print(f"Error deleting session: {e}")
