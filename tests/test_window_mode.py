from types import SimpleNamespace
from screen_sharing.frontend.desktop.window_mode import WindowMode


class Glfw:
    PRESS, RELEASE, REPEAT = 1, 0, 2
    MOD_CONTROL, MOD_ALT = 2, 4
    KEY_ENTER, KEY_KP_ENTER, KEY_ESCAPE = 257, 335, 256
    DONT_CARE = -1
    def __init__(self):
        self.changes = []
        self.closed = False
    def get_window_pos(self, w): return (2100, 150)
    def get_window_size(self, w): return (900, 600)
    def get_monitors(self): return [0, 1]
    def get_monitor_pos(self, m): return (1920 * m, 0)
    def get_video_mode(self, m): return SimpleNamespace(size=SimpleNamespace(width=1920,height=1080),refresh_rate=60)
    def set_window_aspect_ratio(self, *args): pass
    def set_window_monitor(self, *args): self.changes.append(args)
    def set_window_should_close(self, w, value): self.closed = value


def test_fullscreen_uses_current_monitor_and_restores_window():
    glfw = Glfw()
    mode = WindowMode(glfw,'window',lambda: None)
    mode.toggle()
    assert mode.fullscreen
    assert glfw.changes[-1] == ('window',1,0,0,1920,1080,60)
    mode.toggle()
    assert not mode.fullscreen
    assert glfw.changes[-1] == ('window',None,2100,150,900,600,-1)


def test_local_chord_consumes_repeat_and_release_even_after_modifiers_release():
    glfw = Glfw(); released = []
    mode = WindowMode(glfw,'window',lambda: released.append(True))
    assert not mode.handle_key(glfw.KEY_ENTER,glfw.PRESS,0)
    assert mode.handle_key(glfw.KEY_ENTER,glfw.PRESS,6)
    assert mode.handle_key(glfw.KEY_ENTER,glfw.REPEAT,6)
    assert mode.handle_key(glfw.KEY_ENTER,glfw.RELEASE,0)
    assert len(glfw.changes) == 1 and released == [True]
    assert mode.handle_key(glfw.KEY_ESCAPE,glfw.PRESS,6)
    assert glfw.closed
