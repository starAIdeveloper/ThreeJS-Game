"""End-to-end browser checks against a running local app; captures desktop/mobile."""
import json
import os
import atexit
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE=os.environ.get('SPORTSVISION_URL','http://127.0.0.1:8000')
ARTIFACTS=Path('artifacts')
ARTIFACTS.mkdir(exist_ok=True)
if os.environ.get('SPORTSVISION_START_SERVER') == '1':
    server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', '8000'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    atexit.register(server.terminate)
    for _ in range(100):
        try:
            urllib.request.urlopen(BASE+'/api/health', timeout=1).close()
            break
        except OSError:
            time.sleep(.1)
    else:
        raise RuntimeError('Local API did not start')
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True, executable_path=os.environ.get('SPORTSVISION_CHROMIUM'),
                              args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':1536,'height':1100})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE)
    expect(page.locator('h1')).to_contain_text('Football analysis')
    page.locator('#sampleBtn').click()
    expect(page.locator('#sourceBadge')).to_have_text('GENERATED SAMPLE',timeout=90000)
    expect(page.locator('#calBadge')).to_have_text('CALIBRATED')
    assert int(page.locator('#trackCount').inner_text())>0
    page.locator('#video').evaluate('(v)=>{v.currentTime=5;}')
    page.wait_for_function("document.querySelector('#video').readyState>=2")
    page.locator('#eventBtn').click()
    page.locator('#eventKind').select_option('Highlight')
    page.locator('#eventNote').fill('Movement review <script>unsafe</script>')
    page.get_by_role('button',name='Save moment',exact=True).click()
    expect(page.locator('.event-card')).to_contain_text('Movement review <script>unsafe</script>')
    assert page.locator('.event-card script').count()==0
    with page.expect_download() as download:page.locator('#csvLink').click()
    download.value.save_as(ARTIFACTS/'tracks.csv')
    assert 'metres,km/h' in (ARTIFACTS/'tracks.csv').read_text()
    first=page.locator('.player').first
    first.click()
    expect(first).to_have_attribute('aria-pressed','true')
    page.locator('#heatScope').select_option('selected')
    page.screenshot(path=str(ARTIFACTS/'desktop.png'),full_page=True)
    page.locator('#calibrateBtn').click()
    page.locator('#overlay').scroll_into_view_if_needed()
    rect=page.locator('#overlay').bounding_box()
    for x,y in [(40/960,40/540),(920/960,40/540),(920/960,500/540),(40/960,500/540)]:
        page.mouse.click(rect['x']+rect['width']*x,rect['y']+rect['height']*y)
    page.locator('#applyCalibration').click()
    expect(page.locator('#sampleBtn')).to_be_enabled(timeout=90000)
    expect(page.locator('#sourceBadge')).to_have_text('GENERATED SAMPLE')
    expect(page.locator('.event-card')).to_have_count(1)
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(ARTIFACTS/'mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    for sport in ['basketball','volleyball']:
        page.locator(f'[data-sport="{sport}"]').click()
        expect(page.locator('#trackCount')).to_have_text('0')
        page.locator('#sampleBtn').click()
        expect(page.locator('#sourceBadge')).to_have_text('GENERATED SAMPLE',timeout=90000)
        expect(page.locator('h1')).to_contain_text(sport.capitalize())
    # A real file upload takes the uncalibrated path, independently of sample metadata.
    job=page.evaluate("localStorage.getItem('sportsvision-job')")
    source=Path('data')/job/'source.mp4'
    page.locator('#upload').set_input_files(str(source))
    expect(page.locator('#sourceBadge')).to_have_text('UPLOADED CLIP',timeout=90000)
    expect(page.locator('#maxSpeed')).to_have_text('N/A')
    assert not errors,errors
    (ARTIFACTS/'browser-report.json').write_text(json.dumps({'status':'passed','viewports':['1536x1100','390x844'],
        'checks':['sample analysis','playback seek','safe annotation','CSV download','track selection','heatmap filter',
        'four-corner calibration','annotation persistence','mobile overflow','three sports','real upload'],
        'console_errors':errors},indent=2))
    browser.close()
    print('Browser checks passed: desktop, mobile, three sports, upload and calibration')
