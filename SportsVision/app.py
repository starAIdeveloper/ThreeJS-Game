"""Local sports video analysis service. Run: uvicorn app:app --host 127.0.0.1."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="SportsVision", version="1.0.0")

@app.get('/api/health')
def health():
    return {'status': 'ok'}

app.mount('/', StaticFiles(directory=ROOT / 'static', html=True), name='dashboard')
