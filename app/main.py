import uuid
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
import os

from app.services.rag import get_rag_suggestion, ingest_document_from_url
from app.services.database import get_session_history, save_session_history, delete_session

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Cluely V2", description="Meeting/Interview Conversation Assistant")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. Change to specific domains in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sessions are now handled by Supabase for persistence.
# sessions: dict[str, list[dict]] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    history: list[dict] = []

class ChatResponse(BaseModel):
    response: str
    session_id: str

class TranscriptionResponse(BaseModel):
    text: str

class IngestRequest(BaseModel):
    url: str
    filename: str

class TranscriptionRequest(BaseModel):
    text: str

@app.post("/api/transcribe", response_model=TranscriptionResponse)
async def transcribe(request: TranscriptionRequest):
    return TranscriptionResponse(text=request.text)

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    
    # Get history from database
    history = await get_session_history(session_id)
    
    # Add new user message
    history.append({"role": "user", "content": request.message})
    
    # Get RAG suggestion using the history (excluding the current user message for the "history" parameter if needed, 
    # but get_rag_suggestion seems to take the last N messages)
    response_text = await get_rag_suggestion(request.message, chat_history=history[:-1])
    
    # Add assistant response
    history.append({"role": "assistant", "content": response_text})
    
    # Save back to database
    await save_session_history(session_id, history)
    
    return ChatResponse(response=response_text, session_id=session_id)

@app.post("/api/session/clear")
async def clear_session(session_id: str = ""):
    if session_id:
        await delete_session(session_id)
        return {"status": "cleared"}
    return {"status": "session_id_required"}

@app.post("/api/ingest")
async def ingest_file(request: IngestRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(ingest_document_from_url, request.url, request.filename)
    return {"status": "processing", "message": f"File {request.filename} sedang diproses di background."}
