"""Read Omarchy's palette without modifying the desktop's configuration.

Qt handles monitor scale and logical coordinates. No QT_SCALE_FACTOR override:
that would double-scale Wayland windows and break mixed-DPI setups.
"""
import os
from pathlib import Path
try:
    import tomllib
except ImportError:  # Python 3.10
    import tomli as tomllib

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QColor, QPalette


def theme_paths():
    state = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state'))
    config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    return [state / 'omarchy/current/theme/colors.toml', config / 'omarchy/current/theme/colors.toml']


def palette_from_colors(colors, base):
    palette = QPalette(base)
    def color(name, fallback):
        value = QColor(colors.get(name, fallback))
        return value if value.isValid() else QColor(fallback)
    bg = color('background', '#202020')
    fg = color('foreground', '#eeeeee')
    surface = color('lighter_background', bg.name())
    muted = color('light_foreground', fg.name())
    accent = color('accent', fg.name())
    roles = {
        QPalette.ColorRole.Window: bg,
        QPalette.ColorRole.WindowText: fg,
        QPalette.ColorRole.Base: color('dark_background', bg.name()),
        QPalette.ColorRole.AlternateBase: surface,
        QPalette.ColorRole.Text: fg,
        QPalette.ColorRole.Button: surface,
        QPalette.ColorRole.ButtonText: fg,
        QPalette.ColorRole.ToolTipBase: bg,
        QPalette.ColorRole.ToolTipText: fg,
        QPalette.ColorRole.PlaceholderText: muted,
        QPalette.ColorRole.Highlight: accent,
        QPalette.ColorRole.HighlightedText: QColor('#111111') if accent.lightnessF() > .5 else QColor('#ffffff'),
        QPalette.ColorRole.Link: accent,
        QPalette.ColorRole.Light: surface.lighter(140),
        QPalette.ColorRole.Midlight: surface.lighter(115),
        QPalette.ColorRole.Mid: surface.darker(120),
        QPalette.ColorRole.Dark: bg.darker(130),
        QPalette.ColorRole.Shadow: bg.darker(160),
    }
    for role, value in roles.items():
        palette.setColor(role, value)
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, muted)
    return palette


class ThemeController(QObject):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.base = QPalette(app.palette())
        self.signature = None
        self.applied = False
        self.reload()
        self.timer = QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.reload)
        self.timer.start()

    def reload(self):
        for path in theme_paths():
            try:
                source = path.read_bytes()
                if source == self.signature:
                    return
                colors = tomllib.loads(source.decode())
                if 'background' not in colors or 'foreground' not in colors:
                    continue
                if not self.applied:
                    # Fusion is Qt's native Linux widget style and honors QPalette.
                    self.app.setStyle('Fusion')
                    self.applied = True
                self.app.setPalette(palette_from_colors(colors, self.base))
                self.signature = source
                return
            except (OSError, ValueError, TypeError):
                continue
