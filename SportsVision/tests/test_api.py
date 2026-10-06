import time
from fastapi.testclient import TestClient
import app as service
from sample import generate
import pytest

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'DATA',tmp_path)
    with TestClient(service.app) as client: yield client

def wait(client,identity):
    for _ in range(160):
        state=client.get('/api/jobs/'+identity).json()
        if state['status'] in {'ready','error'}:return state
        time.sleep(.1)
    pytest.fail('Background job did not complete')

def test_invalid_uploads_and_unknown_ids(client):
    assert client.post('/api/upload',files={'file':('bad.txt',b'abc')}).status_code==415
    assert client.post('/api/upload',files={'file':('empty.mp4',b'')}).status_code==400
    assert client.get('/api/jobs/'+'a'*32).status_code==404
    assert client.get('/api/jobs/not-an-id/result').status_code==404
    assert client.get('/api/health').json()=={'status':'ok'}

def test_full_upload_calibration_events_and_export(client,tmp_path):
    source=tmp_path/'fixture.mp4';generate(source,seconds=3)
    response=client.post('/api/upload',files={'file':('clip.mp4',source.read_bytes(),'video/mp4')},data={'sport':'football'})
    assert response.status_code==202
    identity=response.json()['id']
    assert wait(client,identity)['status']=='ready'
    result=client.get(f'/api/jobs/{identity}/result').json()
    assert not result['calibrated'] and result['tracks']
    playback=client.get(f'/api/jobs/{identity}/video',headers={'Range':'bytes=0-1023'})
    assert playback.status_code==206 and len(playback.content)==1024
    endpoint=f'/api/jobs/{identity}/events'
    assert client.post(endpoint,json={'time':30,'kind':'Goal'}).status_code==422
    assert client.post(endpoint,json={'time':1.2,'kind':'Pass','note':'Reviewed manually'}).status_code==201
    points=[[40/960,40/540],[920/960,40/540],[920/960,500/540],[40/960,500/540]]
    bad=client.post(f'/api/jobs/{identity}/analyze',json={'points':[[0,0]]*4})
    assert bad.status_code==422
    assert client.post(f'/api/jobs/{identity}/analyze',json={'points':points,'width':105,'height':68}).status_code==202
    assert wait(client,identity)['status']=='ready'
    data=client.get(f'/api/jobs/{identity}/export').json()
    assert data['calibrated'] and data['events'][0]['kind']=='Pass'
    csv=client.get(f'/api/jobs/{identity}/export?format=csv')
    assert csv.status_code==200 and 'metres,km/h' in csv.text

def test_corrupt_upload_reports_error_and_releases_slot(client):
    response=client.post('/api/upload',files={'file':('bad.mp4',b'broken')})
    identity=response.json()['id']
    state=wait(client,identity)
    assert state['status']=='error' and 'decode' in state['error']

def test_sample_is_clearly_identified(client):
    response=client.post('/api/sample?sport=volleyball')
    identity=response.json()['id']
    assert wait(client,identity)['status']=='ready'
    result=client.get(f'/api/jobs/{identity}/result').json()
    assert result['synthetic'] and result['dimensions']==[18,9]
    assert client.post(f'/api/jobs/{identity}/analyze', json={'points':[[.05,.08],[.95,.08],[.95,.92],[.05,.92]],'width':18,'height':9}).status_code==202
    assert wait(client,identity)['status']=='ready'
    assert client.get(f'/api/jobs/{identity}/result').json()['synthetic']
