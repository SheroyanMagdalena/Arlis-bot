# ARLIS AI

ARLIS AI is an Armenian legal research assistant with a React frontend and a
Python retrieval backend. It searches dated ARLIS provisions, filters legal
versions by the requested date, and returns answers with supporting sources.

The repository is a monorepo: the frontend and backend are deployed directly
from this repository. A separate backend repository is not required.

## Project structure

```text
apps/web/                         React + Vite frontend
backend/                          Python retrieval API and pipeline
data/structured/vector_index/    Full local index (not committed)
data/structured/render_index/    Compact 9-provision deployment index
scripts/                          Data, search, and local-run utilities
render.yaml                       Render Blueprint configuration
```

## Local setup

From a PowerShell terminal in the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd apps\web
npm.cmd install
cd ..\..
```

Create a root `.env` file containing your model-provider key:

```dotenv
API_KEY=your_api_key
```

Never commit `.env`.

## Run locally

Start the backend and frontend together:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_live.ps1
```

Open `http://127.0.0.1:5173`.

The backend can also be started separately:

```powershell
.\.venv\Scripts\python.exe -m backend.main `
  --index data\structured\vector_index
```

Then start the frontend in another terminal:

```powershell
cd apps\web
npm.cmd run dev
```

## Date-aware questions

If a question contains a date, the frontend automatically fills the calendar
and sends that date to the backend. For example:

```text
Որքա՞ն էր նվազագույն ամսական աշխատավարձը 2021 թվականի հոկտեմբերին։
```

If a date-dependent question does not contain a date, the UI asks the user to
select one. Relative expressions such as `հիմա` use the current date.

## Data and retrieval

The full local temporal index contains approximately 64,933 chunks and uses
`intfloat/multilingual-e5-small` embeddings combined with BM25 retrieval. It is
not committed because it is approximately 224 MB.

The deployed demo uses `data/structured/render_index`, containing nine curated
legal provisions. Render uses lightweight BM25-first retrieval so the service
fits within the free instance's 512 MiB memory limit. Local full-index usage
continues to use the multilingual embedding model.

The source corpus was last updated in April 2023. Results and externally
generated answers must be checked against the cited ARLIS source before use.

## API

Health check:

```http
GET /api/health
```

Research request:

```http
POST /api/research
Content-Type: application/json

{
  "question": "Որքա՞ն էր նվազագույն աշխատավարձը 2021 թվականին։",
  "target_date": "2021-10-01",
  "top_k": 5
}
```

## Frontend deployment on Vercel

Deploy the `demo` branch from this repository and use `apps/web` as the
frontend application. Set the production environment variable after Render
assigns the backend URL:

```dotenv
VITE_API_URL=https://your-render-service.onrender.com
```

Redeploy Vercel after adding or changing this value.

## Backend deployment on Render

Create a Render Blueprint from this repository and select the `demo` branch.
Render reads `render.yaml`, installs `requirements-render.txt`, and starts the
compact backend with:

```text
python -m backend.main --index data/structured/render_index --lexical-only
```

Set `API_KEY` when Render prompts for it. The Blueprint configures
`FRONTEND_ORIGINS=https://arlis-ai.am` and the `/api/health` health check.

If a previous transformer-based deployment exceeded 512 MiB, choose
**Manual Deploy → Clear build cache & deploy** and confirm Render is deploying
commit `cfa5710` or newer.

## Reproduce Render memory usage with Docker

Build and run the Render-equivalent image with a strict 512 MiB limit:

```powershell
docker build -f Dockerfile.render -t arlis-render-memory-test .
docker run -d --name arlis-memory-test `
  --memory 512m --memory-swap 512m `
  -p 8765:8000 --env-file .env `
  arlis-render-memory-test
docker stats arlis-memory-test
```

Check the service:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/health
```

The lightweight container measured approximately 29–30 MiB locally at idle
and after a test request. Stop and remove it with:

```powershell
docker rm -f arlis-memory-test
```

## Production build and tests

Build the frontend:

```powershell
cd apps\web
npm.cmd run build
```

Run the main backend tests from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.runtime.test_temporal `
  tests.runtime.test_confidence_checker `
  tests.runtime.test_pipeline_rollback `
  tests.retrieval.test_vector_search
```

## Important limitations

- The Render demo index contains only nine curated provisions and cannot answer
  arbitrary Armenian legal questions comprehensively.
- The full source snapshot ends in April 2023; newer questions may use the
  configured external model fallback.
- Similarity and confidence indicators do not guarantee legal correctness.
- Always verify important conclusions against the cited official source.
