# OTT TV Portal — Starter

A starter portal for your own/licensed OTT content.

## Included
- FastAPI backend
- SQLite database
- Admin content CRUD
- TV activation-code flow
- TV-only access middleware
- Cloud upload adapter interface (Cloudflare R2/S3-compatible)
- Simple Netflix-inspired TV UI (without Netflix branding)

## Run
Backend:
```bash
cd backend
python -m venv .venv
# activate the venv
pip install -r requirements.txt
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000/docs`.

Admin:
Open `admin/index.html` in a browser and set API base URL to the backend.

TV:
Open `tv/index.html` in a browser for a demo. Android TV/Fire TV can use the same API endpoints.

## Cloud upload
Set `R2_ENDPOINT`, `R2_ACCESS_KEY`, `R2_SECRET_KEY`, and `R2_BUCKET` in the environment. The upload endpoint returns an object URL. For production, use signed URLs and a CDN rather than exposing private buckets.

This is a starter implementation. Add HTTPS, real admin authentication, rate limiting, device limits, signed playback URLs, and secure secrets before production.
