"""Fullscreen and escape shortcuts, handled before any remote key forwarding."""


class WindowMode:
    def __init__(self, glfw, window, release_keys, disconnect=None):
        self.glfw = glfw
        self.window = window
        self.release_keys = release_keys
        self.disconnect = disconnect or (lambda: glfw.set_window_should_close(window, True))
        self.fullscreen = False
        self.saved_geometry = None
        self.consumed = set()

    def toggle(self):
        g, w = self.glfw, self.window
        if self.fullscreen:
            x, y, width, height = self.saved_geometry
            g.set_window_monitor(w, None, x, y, width, height, g.DONT_CARE)
            self.fullscreen = False
        else:
            wayland = hasattr(g, "get_platform") and g.get_platform() == getattr(g, "PLATFORM_WAYLAND", -2)
            x, y = (0, 0) if wayland else g.get_window_pos(w)
            width, height = g.get_window_size(w)
            self.saved_geometry = (x, y, width, height)
            monitors = g.get_monitors() or []
            if not monitors:
                return
            def overlap(monitor):
                mx, my = g.get_monitor_pos(monitor)
                mode = g.get_video_mode(monitor)
                return max(0, min(x + width, mx + mode.size.width) - max(x, mx)) * max(0, min(y + height, my + mode.size.height) - max(y, my))
            monitor = g.get_primary_monitor() if wayland else max(monitors, key=overlap)
            mode = g.get_video_mode(monitor)
            g.set_window_aspect_ratio(w, g.DONT_CARE, g.DONT_CARE)
            g.set_window_monitor(w, monitor, 0, 0, mode.size.width, mode.size.height, mode.refresh_rate)
            self.fullscreen = True

    def handle_key(self, key, action, mods):
        g = self.glfw
        if key in self.consumed:
            if action == g.RELEASE:
                self.consumed.remove(key)
            return True
        chord = g.MOD_CONTROL | g.MOD_ALT
        if action == g.PRESS and (mods & chord) == chord and key in (g.KEY_ENTER, g.KEY_KP_ENTER, g.KEY_ESCAPE):
            self.consumed.add(key)
            # Ctrl/Alt presses may already have reached the Mac; release them
            # before intercepting the local action so no modifier sticks.
            self.release_keys()
            if key == g.KEY_ESCAPE:
                self.disconnect()
            else:
                self.toggle()
            return True
        return False
