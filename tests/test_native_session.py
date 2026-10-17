import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from dataclasses import replace
import time

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication
import pytest

from screen_sharing.native.session import SessionDialog
from screen_sharing.native.profiles import Profile


@pytest.fixture(scope='module')
def app():
    application = QApplication.instance() or QApplication([])
    application.setQuitOnLastWindowClosed(False)
    return application


def test_failed_connection_stays_native_and_allows_retry(app, monkeypatch):
    monkeypatch.setattr('screen_sharing.native.session.credentials.available',lambda: False)
    profile = replace(Profile.new(),name='Offline Mac',host='127.0.0.1',username='test',port=1)
    dialog = SessionDialog(profile)
    dialog.show()
    dialog.password.setText('test-not-a-real-password')
    dialog.connect_session()
    deadline=time.monotonic()+10
    while dialog.process is not None and time.monotonic()<deadline:
        app.processEvents()
        time.sleep(.01)
    assert dialog.process is None
    assert dialog.isVisible()
    assert dialog.password.text() == ''
    assert dialog.connect_button.text() == 'Retry'
    assert not dialog.connect_button.isEnabled()
    assert not dialog.progress.isVisible()
    assert 'Couldn’t connect' in dialog.status.text()
    assert all('test-not-a-real-password' not in line for line in dialog.logs)
    dialog.hide()


def test_ready_is_parsed_across_reads_and_saves_only_after_connection(app, monkeypatch):
    monkeypatch.setattr('screen_sharing.native.session.credentials.available',lambda: False)
    dialog = SessionDialog(replace(Profile.new(),name='Mac',host='mac.local',username='ted'))
    chunks = iter([b'SCREEN_SHARING_VIEW',b'ER_READY\n'])
    class Process:
        def readAllStandardOutput(self): return next(chunks)
    dialog.process=Process()
    dialog.show()
    dialog.read_output()
    assert not dialog.ready and dialog.isVisible()
    dialog.read_output()
    assert dialog.ready and not dialog.isVisible()
    dialog.process=None


def test_omarchy_palette_changes_without_restart(app, tmp_path, monkeypatch):
    from screen_sharing.native.theme import ThemeController
    from PySide6.QtGui import QPalette
    theme = tmp_path / 'colors.toml'
    monkeypatch.setattr('screen_sharing.native.theme.theme_paths',lambda: [theme])
    theme.write_text('background = "#121212"\nforeground = "#bebebe"\naccent = "#e68e0d"')
    controller = ThemeController(app)
    assert app.palette().color(QPalette.ColorRole.Window).name() == '#121212'
    assert app.palette().color(QPalette.ColorRole.Highlight).name() == '#e68e0d'
    theme.write_text('background = "#eff1f5"\nforeground = "#4c4f69"\naccent = "#8839ef"')
    controller.reload()
    assert app.palette().color(QPalette.ColorRole.Window).name() == '#eff1f5'
    assert app.palette().color(QPalette.ColorRole.Text).name() == '#4c4f69'
    controller.timer.stop()
