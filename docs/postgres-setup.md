# PostgreSQL Setup for VPS

## Docker Run
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

## Connection String
```env
DATABASE_URL=postgresql://cluely_user:ganti-password-kuat@127.0.0.1:5432/cluely
```

Ganti host `127.0.0.1` dengan IP/private network yang sesuai jika backend berjalan di server/container lain.

## Optional Manual SQL
Backend membuat tabel otomatis saat startup, tetapi SQL manualnya:

```sql
CREATE TABLE IF NOT EXISTS chat_sessions (
  session_id TEXT PRIMARY KEY,
  history JSONB NOT NULL DEFAULT '[]'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## Smoke Test
```bash
docker exec -it cluely-postgres psql -U cluely_user -d cluely -c "SELECT NOW();"
docker exec -it cluely-postgres psql -U cluely_user -d cluely -c '\dt'
```
