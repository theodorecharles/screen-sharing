"""Exercise the real GLFW/wgpu viewer with a clearly labeled synthetic frame.

No network connection, credentials, or remote Mac required. Optional --cycle
checks fullscreen -> windowed using the same native keyboard callbacks.
"""
import argparse
import json
from pathlib import Path
import time
from types import SimpleNamespace

import numpy as np
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QPainter, QColor, QFont
from PySide6.QtWidgets import QApplication

from screen_sharing.frontend.desktop import app as viewer
from screen_sharing.proxy.session import SessionConfig
from screen_sharing.proxy.protocol.negotiation import AdvertiseDims
from screen_sharing.proxy.media.tiles import TileFrame

parser = argparse.ArgumentParser()
parser.add_argument('--fullscreen', action='store_true')
parser.add_argument('--cycle', action='store_true')
parser.add_argument('--seconds', type=int, default=16)
parser.add_argument('--report', type=Path)
args = parser.parse_args()
qt = QApplication([])
image = QImage(1280, 800, QImage.Format.Format_RGBA8888)
image.fill(QColor('#20242b'))
p = QPainter(image)
p.setRenderHint(QPainter.RenderHint.Antialiasing)
p.setPen(QColor('#c6d0dd'))
p.setFont(QFont('sans-serif', 13))
p.drawText(48, 50, 'Screen Sharing     /     Viewer check')
p.setPen(QColor('#f2f4f7'))
p.setFont(QFont('sans-serif', 40, QFont.Weight.DemiBold))
p.drawText(80, 285, 'A native window. Your Mac.')
p.setFont(QFont('sans-serif', 17))
p.setPen(QColor('#a8b2c2'))
p.drawText(80, 335, 'Synthetic test image · No remote connection')
p.drawText(80, 615, 'Ctrl + Alt + Enter     Fullscreen / windowed')
p.drawText(80, 655, 'Ctrl + Alt + Escape    Disconnect')
for i,color in enumerate(['#91b5db','#a1c5b7','#dfc695','#cc9ba7']):
 p.fillRect(80+i*140, 395, 124, 90, QColor(color))
p.end()
rgb = np.frombuffer(image.constBits(), np.uint8).reshape(800,1280,4)[:,:,:3].astype(np.float32)
y = .2126*rgb[:,:,0] + .7152*rgb[:,:,1] + .0722*rgb[:,:,2]
u = (rgb[:,:,2]-y)/1.8556+128
v = (rgb[:,:,0]-y)/1.5748+128
planes = [a.clip(0,255).astype(np.uint8).tobytes() for a in (y,u,v)]
frame = TileFrame(*planes,1280,800,1280,1280,1280,800)


class DemoSession:
    canvas_dims = scaled_dims = server_dims = (1280,800)
    num_tiles = 1
    hw_accel = 'synthetic test frame'
    display_rects = []
    display_content_rect = None
    is_connected = True
    def __init__(self, config):
        self.input = SimpleNamespace(key_event=lambda *a: None,pointer_event=lambda *a: None,scroll_event=lambda *a: None)
    def connect(self): pass
    def close(self): pass
    def set_cursor_callback(self, cb): pass
    def wait_for_fresh_tile(self, timeout): time.sleep(.03)
    def get_frame(self, index): return frame


viewer.Session = DemoSession
original_poll = viewer.glfw.poll_events
original_callback = viewer.glfw.set_key_callback
callback = None
window = None
started = time.monotonic()
stage = 0
report = []


def set_callback(w, cb):
    global callback, window
    window, callback = w, cb
    return original_callback(w, cb)


def poll():
    global stage
    original_poll()
    elapsed = time.monotonic() - started
    if window and args.cycle and stage < 3 and elapsed > (4,8,12)[stage]:
        if stage < 2:
            callback(window, viewer.glfw.KEY_ENTER, 0, viewer.glfw.PRESS, viewer.glfw.MOD_CONTROL|viewer.glfw.MOD_ALT)
            callback(window, viewer.glfw.KEY_ENTER, 0, viewer.glfw.RELEASE, 0)
        report.append({'stage':stage,'fullscreen':bool(viewer.glfw.get_window_monitor(window)), 'size':viewer.glfw.get_window_size(window)})
        if args.report:
            args.report.write_text(json.dumps(report,indent=2))
        stage += 1


viewer.glfw.set_key_callback = set_callback
viewer.glfw.poll_events = poll
viewer.run(SessionConfig(host='demo',username='demo',password='',advertise=AdvertiseDims(1280,800,1),audio=False,dynamic_resolution=False),
           title='Screen Sharing — synthetic viewer check',auto_quit_secs=args.seconds,fullscreen=args.fullscreen)
