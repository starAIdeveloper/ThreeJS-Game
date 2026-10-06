import cv2
import numpy as np
import pytest
from vision import Tracker, calibration, project, summarize, analyze_video
from sample import generate

def detection(x, y=.4):
    return {'box':[x,y,.03,.08], 'keypoints':[], 'confidence':None}

def test_projection_known_rectangle():
    matrix=calibration([[.1,.2],[.9,.2],[.9,.8],[.1,.8]], (28.,15.))
    assert project([.5,.5],matrix)==pytest.approx([14,7.5])
    assert project([.9,.8],matrix)==pytest.approx([28,15],abs=1e-5)

@pytest.mark.parametrize('points', [[],[[0,0]]*4,[[0,0],[1,1],[1,0],[0,1]],[[0,0],[2,0],[1,1],[0,1]],[[0,0],[1,0],[1,float('nan')],[0,1]]])
def test_bad_calibration_rejected(points):
    with pytest.raises(ValueError): calibration(points,(105,68))

def test_ids_survive_detection_reordering_and_short_gap():
    tracker=Tracker()
    first=tracker.update([detection(.2),detection(.7)],0)
    tracker.update([], .1)
    later=tracker.update([detection(.71),detection(.21)],.2)
    assert [t['id'] for t in later]==[first[1]['id'],first[0]['id']]

def test_expired_tracks_do_not_claim_new_identity():
    tracker=Tracker()
    first=tracker.update([detection(.2)],0)[0]['id']
    assert tracker.update([detection(.2)],1)[0]['id']!=first

def test_one_detection_cannot_be_assigned_to_two_tracks():
    tracker=Tracker()
    tracker.update([detection(.2),detection(.23)],0)
    assert len(tracker.update([detection(.22)],.1))==1

def frames(points,times):
    return [{'time':time,'detections':[{'id':1,'point':[x/100,y/100],'world':[x,y]}]} for (x,y),time in zip(points,times)]

def test_metrics_use_elapsed_seconds_and_convert_kmh():
    track=summarize(frames([[0,0],[.4,0],[.8,0]],[0,.1,.2]),(105,68),True)[0]
    assert track['distance']==pytest.approx(.8)
    assert track['max_speed']==pytest.approx(14.4)

def test_gaps_and_impossible_jumps_are_not_counted():
    track=summarize(frames([[0,0],[30,0],[30.1,0]],[0,.1,1.5]),(105,68),True)[0]
    assert track['distance']==0
    assert track['rejected_segments']==2

@pytest.mark.parametrize('sport',['football','basketball','volleyball'])
def test_generated_video_produces_actual_motion_tracks(tmp_path,sport):
    path=tmp_path/'sample.mp4'
    generate(path,sport,seconds=3)
    result=analyze_video(path)
    assert result['duration']==pytest.approx(3)
    assert result['tracks'] and len(result['frames'])==25
    assert any(len(t['samples'])>10 for t in result['tracks'])
    assert not result['calibrated']
    assert result['events']==[]

def test_corrupt_video_fails_with_readable_message(tmp_path):
    path=tmp_path/'broken.mp4';path.write_bytes(b'not a video')
    with pytest.raises(ValueError,match='decode'):analyze_video(path)
