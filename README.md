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
- **Database Session**: Backend memakai PostgreSQL langsung melalui `DATABASE_URL`. Kalau `DATABASE_URL` tidak diisi, backend fallback ke `127.0.0.1:5432` dengan default `DB_NAME=cluely`, `DB_USER=password`, `DB_PASSWORD=password`.

## Docker Compose PostgreSQL

Kalau hanya ingin menyalakan container PostgreSQL, gunakan:

```bash
docker compose up -d postgres
```

Compose ini hanya menjalankan service `postgres`, dengan env:

```env
DB_NAME=cluely
DB_USER=password
DB_PASSWORD=password
DB_PORT=5432
```

## Setup PostgreSQL Lokal / VPS

Backend ini memakai PostgreSQL biasa untuk menyimpan `chat_sessions`.

### 1. Jalankan PostgreSQL di Docker
```bash
docker run -d \
  --name cluely-postgres \
  --restart unless-stopped \
  -e POSTGRES_DB=cluely \
  -e POSTGRES_USER=cluely_user \
  -e POSTGRES_PASSWORD=ganti-password-kuat \
  -p 5432:5432 \
  -v cluely-postgres-data:/var/lib/postgresql/data \
  postgres:16
```

### 2. Set `.env` backend di VPS
```env
DATABASE_URL=postgresql://cluely_user:ganti-password-kuat@IP_VPS_ANDA:5432/cluely
GROQ_API_KEY=your-groq-key
JINA_API_KEY=your-jina-key
QDRANT_URL=your-qdrant-cloud-url
QDRANT_API_KEY=your-qdrant-api-key
```

### 3. Setup lokal

Kalau PostgreSQL lokal kamu jalan di Docker dengan kredensial default latihan:

```bash
docker run -d \
  --name cluely-postgres \
  --restart unless-stopped \
  -e POSTGRES_DB=cluely \
  -e POSTGRES_USER=password \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  -v cluely-postgres-data:/var/lib/postgresql/data \
  postgres:16
```

Backend lokal akan otomatis mencoba konek ke:

```text
postgresql://password:password@127.0.0.1:5432/cluely
```

Kalau mau override, cukup isi env berikut:

```env
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=cluely
DB_USER=password
DB_PASSWORD=password
```

### 4. Tabel session
Tabel `chat_sessions` akan dibuat otomatis saat backend startup. Skemanya:

```sql
CREATE TABLE IF NOT EXISTS chat_sessions (
  session_id TEXT PRIMARY KEY,
  history JSONB NOT NULL DEFAULT '[]'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 5. Cek koneksi dari VPS
```bash
docker exec -it cluely-postgres psql -U cluely_user -d cluely -c '\dt'
```

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
