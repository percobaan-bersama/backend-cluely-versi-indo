## Base URL
Default development URL: `http://localhost:8000`

## Endpoints

### 1. Transkripsi Audio
Mengirimkan teks transkripsi dari frontend ke backend (echo).
- **URL**: `/api/transcribe`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "text": "Teks hasil transkripsi dari Whisper FE"
  }
  ```

### 2. Chat & AI Suggestion (RAG)
Mendapatkan saran AI berdasarkan pesan user dan riwayat percakapan.
- **URL**: `/api/chat`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "message": "Apa poin penting dari diskusi tadi?",
    "session_id": "uuid-string-opsional",
    "history": []
  }
  ```
- **Response**:
  - `response`: Jawaban dari AI.
  - `session_id`: ID sesi saat ini (gunakan ini untuk request berikutnya agar riwayat terjaga).

### 3. Clear Session
Menghapus riwayat sesi tertentu.
- **URL**: `/api/session/clear`
- **Method**: `POST`
- **Query Params**: `session_id=...`

### 4. Knowledge Base Ingest (Background)
Menginstruksikan backend untuk mengambil dokumen dari URL (misal: S3/UploadThing) dan menyimpannya ke RAG.
- **URL**: `/api/ingest`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "url": "https://example.com/document.pdf",
    "filename": "document.pdf"
  }
  ```

## Detail Teknis
- **CORS**: Sudah diaktifkan untuk semua origin (`*`) pada lingkungan development.
- **Authentication**: Saat ini tidak memerlukan auth header, namun pastikan API Key sudah terpasang di `.env` backend.
- **Format Data**: Selalu gunakan `Content-Type: application/json` kecuali untuk upload file.

## Contoh Integrasi (Fetch API)
```javascript
const response = await fetch('http://localhost:8000/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Halo, siapa namamu?',
    session_id: currentSessionId
  })
});
const data = await response.json();
console.log(data.response);
```
