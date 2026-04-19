import uuid
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import json

import asyncio
from app.services.rag import RAG
from app.services.llm import LLM
from app.services.database import Database

from fastapi.middleware.cors import CORSMiddleware
db = Database()
rag = RAG()
app = FastAPI(title="Cluely V2", description="Meeting/Interview Conversation Assistant")
llm = LLM()
@app.on_event("startup")
async def startup_event():
    await db.initialize_database()
    await rag.initialize_rag_service()


@app.on_event("shutdown")
async def shutdown_event():
    await db.close_database()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

@app.post("/api/chat")
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    
    history_task = db.get_session_history(session_id)
    index_empty_task = rag.is_index_empty()
    
    history, rag_empty = await asyncio.gather(history_task, index_empty_task)
    
    history.append({"role": "user", "content": request.message})
    
    
    if rag_empty:
        print("RAG is empty, falling back to standard LLM")
        response_stream = llm.get_streaming_response(conversation_history=history)
    else:
        response_stream = await rag.get_rag_suggestion(request.message, chat_history=history[:-1])
        print("wait for RAG")
    
    async def event_generator():
        full_response = ""
        
        try:
            if hasattr(response_stream, "async_response_gen"):
                async for chunk in response_stream.async_response_gen():
                    if isinstance(chunk, str):
                        token = chunk
                    else:
                        token = getattr(chunk, 'delta', None) or str(chunk)
                    
                    if token:
                        full_response += token
                        yield token
            else:
                async for token in response_stream:
                    if token:
                        full_response += token
                        yield token
        except Exception as e:
            print(f"Error in event_generator: {e}")
            yield f"\n[Error: {str(e)}]"

        if full_response:
            history.append({"role": "assistant", "content": full_response})
            await db.save_session_history(session_id, history)
    
    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream", 
        headers={
            "X-Session-ID": session_id,
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/session/clear")
async def clear_session(session_id: str = ""):
    if session_id:
        await db.delete_session(session_id)
        return {"status": "cleared"}
    return {"status": "session_id_required"}

@app.get("/api/history")
async def get_history():
    sessions = await db.get_all_sessions()
    return {"sessions": sessions}

@app.get("/api/history/{session_id}")
async def get_session_history(session_id: str):
    history = await db.get_session_by_id(session_id)
    return {"history": history}

@app.post("/api/ingest")
async def ingest_file(request: IngestRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(rag.ingest_document_from_url, request.url, request.filename)
    return {"status": "processing", "message": f"File {request.filename} sedang diproses di background."}
