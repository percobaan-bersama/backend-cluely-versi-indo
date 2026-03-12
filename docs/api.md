# Cluely API Reference

Cluely provides a simple API for audio transcription and Retrieval-Augmented Generation (RAG) based chat for meeting and interview assistance.

## Base URL
The API is served from the same host as the frontend. If running locally, the base URL is typically `http://localhost:8000`.

## Endpoints

### 1. Transcribe Audio (JSON)
Receives transcribed text directly from the frontend.

- **URL:** `/api/transcribe`
- **Method:** `POST`
- **Content-Type:** `application/json`
- **Request Body:**
  ```json
  {
    "text": "The transcribed text here"
  }
  ```
- **Response:**
  - `text` (string): The echoed transcribed text.

**Example Request (curl):**
```bash
curl -X POST http://localhost:8000/api/transcribe \
  -H "Content-Type: application/json" \
  -d '{"text": "Halo dunnia"}'
```

---

### 2. Chat / RAG Suggestion
Generates an LLM response based on the provided message and conversation history, using RAG for context.

- **URL:** `/api/chat`
- **Method:** `POST`
- **Content-Type:** `application/json`
- **Request Body:**
  ```json
  {
    "message": "What was discussed earlier?",
    "session_id": "optional-uuid-string",
    "history": []
  }
  ```
- **Response:**
  - `response` (string): The AI generated response.
  - `session_id` (string): The current session ID (newly generated if not provided).

**Example Request (curl):**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "session_id": ""}'
```

---

### 3. Clear Session
Clears the conversation history for a specific session from the database.

- **URL:** `/api/session/clear`
- **Method:** `POST`
- **Parameters:**
  - `session_id` (query parameter): The ID of the session to clear.
- **Response:**
  - `status` (string): Either `"cleared"` or `"session_id_required"`.

**Example Request (curl):**
```bash
curl -X POST "http://localhost:8000/api/session/clear?session_id=your-session-id"
```

---

### 4. Ingest File (Background)
Ingests a document from a URL into the RAG system. This process runs in the background.

- **URL:** `/api/ingest`
- **Method:** `POST`
- **Content-Type:** `application/json`
- **Request Body:**
  ```json
  {
    "url": "https://example.com/document.pdf",
    "filename": "document.pdf"
  }
  ```
- **Response:**
  - `status` (string): `"processing"`
  - `message` (string): Confirmation that the file is being processed.

**Example Request (curl):**
```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/document.pdf", "filename": "document.pdf"}'
```

