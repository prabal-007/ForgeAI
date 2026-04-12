Here is a concise **run checklist** for your setup (Windows + Docker Postgres + repo at `C:\ps\ForgeAI`).

### 1. Postgres in Docker

Container should be running (`docker ps` shows `forgeai`). Create the app database once if you have not already:

```powershell
docker exec -it forgeai psql -U postgres -c "CREATE DATABASE forgeai;"
```

(If it already exists, you will see an error—safe to ignore.)

### 2. `forgeai/.env`

From `C:\ps\ForgeAI\forgeai`, ensure `.env` has at least:

- `OPENAI_API_KEY=...` (required for agents and real covers)
- `DATABASE_URL=postgresql+psycopg://postgres:mypassword@localhost:5432/forgeai`  
  (use your real password and DB name if different)

### 3. Python env and dependencies

```powershell
cd C:\ps\ForgeAI\forgeai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 4. Start the API

Still in `C:\ps\ForgeAI\forgeai`:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

That matches what `run.sh` does (`uvicorn app.main:app --reload`), with an explicit host/port so you always know where to point a browser or `curl`.

### 5. Smoke test

- Open: `http://127.0.0.1:8000/` (should return a small JSON message)
- Docs: `http://127.0.0.1:8000/docs`

### 6. Typical API flow (optional)

1. `POST http://127.0.0.1:8000/pipeline/products` with body `{"brief": "..."}`  
2. `POST http://127.0.0.1:8000/pipeline/{product_id}/run` — repeat and `approve` until the pipeline advances (use `/docs` to try it interactively).

**Important:** Always run Uvicorn with the **current directory** set to `forgeai` so `app` imports and `.env` loading behave as intended.