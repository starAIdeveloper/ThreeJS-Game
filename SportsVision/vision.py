"""Detection, short-lived track IDs and calibrated planar motion estimates."""
import math
from pathlib import Path
import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

SPORTS = {'football': (105., 68.), 'basketball': (28., 15.), 'volleyball': (18., 9.)}

def calibration(points, dimensions):
    if len(points) != 4:
        raise ValueError('Select four court corners: top-left, top-right, bottom-right, bottom-left.')
    p = np.asarray(points, dtype=np.float32)
    if p.shape != (4, 2) or not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError('Corners must be finite normalized coordinates between 0 and 1.')
    if not cv2.isContourConvex(p.reshape(-1, 1, 2)) or abs(cv2.contourArea(p)) < .01:
        raise ValueError('Corners must form a non-crossing convex court with sufficient area.')
    width, height = dimensions
    if not all(math.isfinite(v) and 1 <= v <= 200 for v in dimensions):
        raise ValueError('Court dimensions must be between 1 and 200 metres.')
    target = np.array([[0, 0], [width, 0], [width, height], [0, height]], dtype=np.float32)
    return cv2.getPerspectiveTransform(p, target)

def project(point, matrix):
    a = matrix @ np.array([*point, 1.])
    if abs(a[2]) < 1e-8:
        return None
    return (a[:2] / a[2]).tolist()

class Tracker:
    """Hungarian assignment with velocity prediction, distance gate and expiry."""
    def __init__(self, gate=.10, ttl=.7):
        self.gate, self.ttl = gate, ttl
        self.tracks, self.next_id = {}, 1

    def update(self, detections, time):
        self.tracks = {i: t for i, t in self.tracks.items() if time - t['time'] <= self.ttl}
        ids = list(self.tracks)
        centres = np.array([[d['box'][0] + d['box'][2] / 2, d['box'][1] + d['box'][3]] for d in detections])
        matched = {}
        if ids and len(centres):
            predictions = [self.tracks[i]['point'] + self.tracks[i]['velocity'] * (time-self.tracks[i]['time']) for i in ids]
            distances = np.linalg.norm(np.array(predictions)[:, None] - centres[None, :], axis=2)
            rows, cols = linear_sum_assignment(distances)
            matched = {int(c): ids[int(r)] for r, c in zip(rows, cols) if distances[r, c] <= self.gate}
        output = []
        for n, detection in enumerate(detections):
            identity = matched.get(n)
            if identity is None:
                identity, self.next_id = self.next_id, self.next_id + 1
            old = self.tracks.get(identity)
            dt = time - old['time'] if old else 0
            velocity = (centres[n] - old['point']) / dt if dt > 0 else np.zeros(2)
            self.tracks[identity] = {'point': centres[n], 'velocity': velocity, 'time': time}
            output.append(dict(detection, id=identity, point=centres[n].tolist()))
        return output

class MotionDetector:
    """Foreground candidates for fixed cameras. Not a semantic player detector."""
    def __init__(self):
        self.model = cv2.createBackgroundSubtractorMOG2(history=120, varThreshold=30, detectShadows=False)

    def __call__(self, frame):
        h, w = frame.shape[:2]
        mask = self.model.apply(frame)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 5), np.uint8))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections = []
        for c in contours:
            x, y, bw, bh = cv2.boundingRect(c)
            if 35 < cv2.contourArea(c) < w*h*.04 and bw > 3 and bh > 8:
                detections.append({'box': [x/w, y/h, bw/w, bh/h], 'confidence': None, 'keypoints': []})
        return sorted(detections, key=lambda d: d['box'][2]*d['box'][3], reverse=True)[:40]

class PoseDetector:
    def __init__(self, weights):
        from ultralytics import YOLO
        if not Path(weights).is_file():
            raise ValueError('SPORTSVISION_POSE_WEIGHTS must point to an existing local pose model.')
        self.model = YOLO(weights)

    def __call__(self, frame):
        h, w = frame.shape[:2]
        result = self.model.predict(frame, classes=[0], conf=.4, verbose=False)[0]
        output = []
        for i, box in enumerate(result.boxes):
            x1, y1, x2, y2 = box.xyxy[0].cpu().tolist()
            keys = result.keypoints.data[i].cpu().tolist() if result.keypoints is not None else []
            output.append({'box':[x1/w, y1/h, (x2-x1)/w, (y2-y1)/h], 'confidence':float(box.conf[0]),
                           'keypoints':[[x/w, y/h, c] for x,y,c in keys]})
        return output

def summarize(frames, dimensions, calibrated):
    tracks = {}
    for frame in frames:
        for d in frame['detections']:
            t = tracks.setdefault(d['id'], {'id':d['id'], 'samples':[], 'distance':0., 'max_speed':0., 'rejected_segments':0})
            p = d['world'] if calibrated else d['point']
            sample = {'time':frame['time'], 'point':p, 'image_point':d['point'], 'speed':None}
            if t['samples']:
                old = t['samples'][-1]
                dt = sample['time']-old['time']
                delta = math.dist(p, old['point'])
                speed = delta/dt if dt > 0 else 0
                if 0 < dt <= .8 and (not calibrated or speed <= 15):
                    sample['speed'] = speed * (3.6 if calibrated else 1)
                    t['distance'] += delta
                    t['max_speed'] = max(t['max_speed'], sample['speed'])
                else:
                    t['rejected_segments'] += 1
            t['samples'].append(sample)
    output = []
    for t in tracks.values():
        speeds = [s['speed'] for s in t['samples'] if s['speed'] is not None]
        t['avg_speed'] = sum(speeds)/len(speeds) if speeds else 0
        t['distance'] = round(t['distance'], 3)
        t['max_speed'] = round(t['max_speed'], 2)
        t['avg_speed'] = round(t['avg_speed'], 2)
        output.append(t)
    return sorted(output, key=lambda t:len(t['samples']), reverse=True)

def analyze_video(path, detector=None, points=None, dimensions=(105.,68.), progress=lambda value:None):
    matrix = calibration(points, dimensions) if points else None
    detector = detector or MotionDetector()
    cap = cv2.VideoCapture(str(path))
    try:
        fps, count = cap.get(cv2.CAP_PROP_FPS), cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if not cap.isOpened() or not math.isfinite(fps) or fps <= 0 or count <= 0:
            raise ValueError('Could not decode this video. Try an MP4 with H.264 video.')
        if count/fps > 180:
            raise ValueError('Use clips up to 3 minutes. Split longer recordings first.')
        stride, tracker, frames, n = max(1, math.ceil(fps/10)), Tracker(), [], 0
        while True:
            ok, frame = cap.read()
            if not ok: break
            if n % stride == 0:
                h,w = frame.shape[:2]
                if max(h,w) > 960:
                    frame = cv2.resize(frame, (round(w*960/max(h,w)), round(h*960/max(h,w))))
                detections = tracker.update(detector(frame), n/fps)
                for d in detections:
                    d['world'] = project(d['point'], matrix) if matrix is not None else None
                if matrix is not None:
                    detections = [d for d in detections if d['world'] is not None and 0 <= d['world'][0] <= dimensions[0] and 0 <= d['world'][1] <= dimensions[1]]
                frames.append({'time':round(n/fps, 5), 'detections':detections})
                if n % (stride*10) == 0: progress(min(.95, n/count))
            n += 1
        if not frames: raise ValueError('Video contains no decodable frames.')
        return {'fps':fps, 'duration':n/fps, 'width':w, 'height':h, 'sample_rate':fps/stride,
                'calibrated':matrix is not None, 'dimensions':dimensions, 'frames':frames,
                'tracks':summarize(frames, dimensions, matrix is not None), 'events':[]}
    finally:
        cap.release()
