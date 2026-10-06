"""Local sports video analysis service. Run: uvicorn app:app --host 127.0.0.1."""
import csv
import io
import json
import os
import re
import shutil
import subprocess
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from vision import SPORTS, PoseDetector, analyze_video, calibration
from sample import generate

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="SportsVision", version="1.0.0")
DATA = Path(os.environ.get('SPORTSVISION_DATA', str(ROOT / 'data')))
DATA.mkdir(parents=True, exist_ok=True)
executor = ThreadPoolExecutor(max_workers=1)
slots = threading.BoundedSemaphore(4)
lock = threading.RLock()
jobs = {}

class Options(BaseModel):
    points: list[list[float]] | None = None
    width: float = Field(default=105, ge=1, le=200)
    height: float = Field(default=68, ge=1, le=200)

class Event(BaseModel):
    time: float = Field(ge=0)
    kind: Literal['Pass','Shot','Goal','Foul','Highlight']
    note: str = Field(default='', max_length=160)

def folder(identity):
    if not re.fullmatch('[a-f0-9]{32}', identity): raise HTTPException(404, 'Analysis not found')
    p = DATA / identity
    if not p.is_dir(): raise HTTPException(404, 'Analysis not found')
    return p

def read_result(identity):
    p = folder(identity) / 'result.json'
    if not p.exists(): raise HTTPException(409, 'Analysis is not ready')
    with lock: return json.loads(p.read_text())

def write_result(p, result):
    with lock:
        temp = p / 'result.tmp'
        temp.write_text(json.dumps(result, allow_nan=False))
        temp.replace(p / 'result.json')

def run(identity, source, sport, options, synthetic=False):
    try:
        p=folder(identity)
        if synthetic: generate(source, sport)
        previous = read_result(identity) if (p/'result.json').exists() else None
        def progress(value):
            with lock: jobs[identity]['progress'] = round(value*90)
        weights = os.environ.get('SPORTSVISION_POSE_WEIGHTS')
        detector = PoseDetector(weights) if weights else None
        result = analyze_video(source, detector=detector, points=options.points,
                               dimensions=(options.width, options.height), progress=progress)
        is_synthetic = synthetic or bool(previous and previous['synthetic'])
        result.update(id=identity, sport=sport, synthetic=is_synthetic,
                      detector='pose' if weights else 'motion', title='Generated training clip' if is_synthetic else 'Uploaded video')
        if previous: result['events']=previous['events']
        with lock: jobs[identity]['progress']=94
        if not shutil.which('ffmpeg'): raise RuntimeError('Install ffmpeg for browser-compatible playback.')
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(source),'-an','-vf',
                        "scale='min(960,iw)':-2",'-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p',
                        '-movflags','+faststart',str(p/'playback.tmp.mp4')], check=True, capture_output=True, timeout=240)
        (p/'playback.tmp.mp4').replace(p/'playback.mp4')
        write_result(p,result)
        with lock: jobs[identity].update(status='ready',progress=100)
    except Exception as error:
        with lock: jobs[identity].update(status='error',error=str(error)[:400])
    finally: slots.release()

def queue(identity, source, sport, options, synthetic=False):
    with lock: jobs[identity]={'id':identity,'status':'queued','progress':0}
    def work():
        with lock: jobs[identity]['status']='processing'
        run(identity,source,sport,options,synthetic)
    executor.submit(work)
    return jobs[identity].copy()

def validate_options(options):
    if options.points is not None:
        try: calibration(options.points,(options.width,options.height))
        except ValueError as error: raise HTTPException(422,str(error))

@app.post('/api/upload',status_code=202)
async def upload(file: UploadFile = File(...), sport: str = Form('football')):
    if sport not in SPORTS: raise HTTPException(422,'Unsupported sport')
    if Path(file.filename or '').suffix.lower() not in {'.mp4','.mov','.avi','.mkv','.webm'}:
        raise HTTPException(415,'Use MP4, MOV, AVI, MKV or WebM video')
    if not slots.acquire(blocking=False): raise HTTPException(429,'Analysis queue full. Try again shortly.')
    identity=uuid.uuid4().hex
    p=DATA/identity
    p.mkdir()
    source=p/'source.mp4'
    try:
        size=0
        with source.open('wb') as out:
            while chunk := await file.read(1024*1024):
                size+=len(chunk)
                if size>200*1024*1024: raise HTTPException(413,'Maximum upload size is 200 MB')
                out.write(chunk)
        if size==0: raise HTTPException(400,'Video is empty')
        width,height=SPORTS[sport]
        return queue(identity,source,sport,Options(width=width,height=height))
    except Exception:
        shutil.rmtree(p,ignore_errors=True)
        slots.release()
        raise
    finally: await file.close()

@app.post('/api/sample',status_code=202)
def sample(sport: Literal['football','basketball','volleyball']='football'):
    if not slots.acquire(blocking=False): raise HTTPException(429,'Analysis queue full')
    identity=uuid.uuid4().hex
    p=DATA/identity
    p.mkdir()
    width,height=SPORTS[sport]
    options=Options(width=width,height=height,points=[[40/960,40/540],[920/960,40/540],[920/960,500/540],[40/960,500/540]])
    return queue(identity,p/'source.mp4',sport,options,synthetic=True)

@app.get('/api/jobs/{identity}')
def status(identity: str):
    p=folder(identity)
    with lock:
        if identity in jobs: return jobs[identity].copy()
    if (p/'result.json').exists(): return {'id':identity,'status':'ready','progress':100}
    return {'id':identity,'status':'error','error':'Processing interrupted. Upload this clip again.'}

@app.get('/api/jobs/{identity}/result')
def result(identity: str): return read_result(identity)

@app.get('/api/jobs/{identity}/video')
def video(identity: str):
    p=folder(identity)/'playback.mp4'
    if not p.exists(): raise HTTPException(409,'Playback is not ready')
    return FileResponse(p, media_type='video/mp4')

@app.post('/api/jobs/{identity}/analyze',status_code=202)
def reanalyze(identity: str, options: Options):
    p=folder(identity)
    validate_options(options)
    with lock:
        if jobs.get(identity,{}).get('status') in {'queued','processing'}: raise HTTPException(409,'Already processing')
        result=read_result(identity)
        if not slots.acquire(blocking=False): raise HTTPException(429,'Analysis queue full')
        return queue(identity,p/'source.mp4',result['sport'],options)

@app.post('/api/jobs/{identity}/events',status_code=201)
def add_event(identity: str, event: Event):
    with lock:
        if jobs.get(identity,{}).get('status') in {'queued','processing'}: raise HTTPException(409,'Wait for analysis to finish')
        result=read_result(identity)
        if event.time>result['duration']: raise HTTPException(422,'Event time exceeds clip duration')
        result['events'].append(event.model_dump())
        result['events'].sort(key=lambda e:e['time'])
        write_result(folder(identity),result)
        return result['events']

@app.get('/api/jobs/{identity}/export')
def export(identity: str, format: Literal['json','csv']='json'):
    result=read_result(identity)
    if format=='json':
        return Response(json.dumps(result),media_type='application/json',headers={'Content-Disposition':'attachment; filename=analysis.json'})
    output=io.StringIO()
    writer=csv.writer(output)
    writer.writerow(['track_id','time_seconds','x','y','speed','position_unit','speed_unit'])
    for track in result['tracks']:
        for s in track['samples']:
            writer.writerow([track['id'],s['time'],*s['point'],s['speed'],'metres' if result['calibrated'] else 'normalized_image','km/h' if result['calibrated'] else 'normalized_image/s'])
    return Response(output.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=tracks.csv'})

@app.get('/api/health')
def health():
    return {'status': 'ok'}

app.mount('/', StaticFiles(directory=ROOT / 'static', html=True), name='dashboard')
