"""Generate original fixed-camera test footage; no match footage or fake metrics."""
import math
import cv2
import numpy as np

def generate(path, sport='football', seconds=12):
    w, h, fps = 960, 540, 25
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (w,h))
    if not writer.isOpened(): raise RuntimeError('MP4 encoder unavailable')
    try:
        for n in range(seconds*fps):
            f = np.zeros((h,w,3), dtype=np.uint8)
            f[:] = (28,51,18) if sport=='football' else (52,82,114)
            for x in range(40,920,110):
                cv2.rectangle(f,(x,40),(x+55,500),(34,65,24) if sport=='football' else (56,88,122),-1)
            white=(155,195,167)
            cv2.rectangle(f,(40,40),(920,500),white,2)
            cv2.line(f,(480,40),(480,500),white,2)
            if sport=='football':
                cv2.circle(f,(480,270),70,white,2)
                for x in [40,800]: cv2.rectangle(f,(x,160),(x+120,380),white,2)
            elif sport=='basketball':
                cv2.circle(f,(480,270),60,white,2)
                for x in [80,880]: cv2.circle(f,(x,270),130,white,2)
            else:
                for x in [330,630]: cv2.line(f,(x,40),(x,500),white,2)
            for i in range(6):
                t=n/fps
                x=int(160+i*118 + 46*math.sin(t*.6+i))
                y=int(180+(i%2)*150 + 65*math.sin(t*.4+i*.8))
                color=(240,158,48) if i%2 else (97,227,50)
                cv2.ellipse(f,(x,y),(9,18),0,0,360,color,-1)
                cv2.circle(f,(x,y-24),7,(140,183,223),-1)
                cv2.line(f,(x-5,y+13),(x-8,y+27),(211,215,220),4)
                cv2.line(f,(x+5,y+13),(x+8,y+27),(211,215,220),4)
            cv2.putText(f,'GENERATED TEST FOOTAGE',(48,525),cv2.FONT_HERSHEY_SIMPLEX,.45,(205,215,205),1)
            writer.write(f)
    finally: writer.release()
