"""Native sign-in/progress window for a single saved Mac; no browser or manager."""
import argparse
from collections import deque
from dataclasses import replace
import os
import sys

from PySide6.QtCore import QEvent, QProcess, QProcessEnvironment, QSize, QTimer, Qt
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QHBoxLayout, QLabel,
                              QLineEdit, QMessageBox, QProgressBar, QPushButton,
                              QVBoxLayout, QWidget)

from . import credentials
from .commands import find
from .profiles import ProfileStore, session_arguments
from .shortcuts import icon_path
from .theme import ThemeController


class SessionDialog(QDialog):
    def __init__(self, profile):
        super().__init__()
        self.profile = profile
        self.process = None
        self.cancelled = False
        self.ready = False
        self.secret = None
        self.logs = deque(maxlen=100)
        self.output = ""
        self.setWindowTitle(f"{profile.name} — Screen Sharing")
        self.setWindowIcon(QIcon(str(icon_path(profile.machine))))
        self.setFixedWidth(440)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        artwork = self.artwork = QLabel()
        artwork.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_artwork()
        layout.addWidget(artwork)
        name = QLabel(profile.name)
        name.setTextFormat(Qt.TextFormat.PlainText)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = name.font()
        font.setPointSize(19)
        font.setWeight(QFont.Weight.DemiBold)
        name.setFont(font)
        layout.addWidget(name)
        self.status = QLabel(f"Sign in as {profile.username}")
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.form = QWidget()
        form = QVBoxLayout(self.form)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(12)
        self.password = QLineEdit()
        self.password.setPlaceholderText("Mac password")
        self.password.setAccessibleName("Mac password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setMinimumHeight(36)
        form.addWidget(self.password)
        self.remember = QCheckBox("Remember in system keyring")
        self.remember.setEnabled(credentials.available())
        self.remember.setChecked(profile.remember_password and self.remember.isEnabled())
        if not self.remember.isEnabled():
            self.remember.setToolTip("A Secret Service or KWallet keyring is needed to save passwords.")
        form.addWidget(self.remember)
        layout.addWidget(self.form)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.hide()
        layout.addWidget(self.progress)
        hint = QLabel("Ctrl+Alt+Enter  ·  Fullscreen\nCtrl+Alt+Escape  ·  Disconnect")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setForegroundRole(self.palette().ColorRole.PlaceholderText)
        layout.addWidget(hint)
        footer = QHBoxLayout()
        mode = QLabel("Fullscreen" if profile.fullscreen else "Windowed")
        mode.setForegroundRole(self.palette().ColorRole.PlaceholderText)
        footer.addWidget(mode)
        footer.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        self.connect_button = QPushButton("Connect")
        self.connect_button.setDefault(True)
        self.connect_button.clicked.connect(self.connect_session)
        self.connect_button.setEnabled(False)
        self.password.textChanged.connect(lambda text: self.connect_button.setEnabled(bool(text)))
        footer.addWidget(self.connect_button)
        layout.addLayout(footer)
        self.password.setFocus()

    def update_artwork(self):
        self.artwork.setPixmap(QIcon(str(icon_path(self.profile.machine))).pixmap(
            QSize(136, 136), self.devicePixelRatioF()))

    def event(self, event):
        result = super().event(event)
        if event.type() in (QEvent.Type.DevicePixelRatioChange, QEvent.Type.Show) and hasattr(self, "artwork"):
            self.update_artwork()
        return result

    def autoconnect(self):
        if not self.profile.remember_password:
            return
        try:
            password = credentials.get(self.profile.id)
            if password:
                self.password.setText(password)
                self.connect_session()
        except Exception:
            self.status.setText("Unlock your keyring or enter your Mac password.")

    def connect_session(self):
        if self.process is not None:
            return
        password = self.password.text()
        if not password or "\n" in password or "\r" in password:
            return
        self.secret = password if self.remember.isChecked() else None
        self.cancelled = self.ready = False
        self.logs.clear()
        self.output = ""
        self.form.hide()
        self.progress.show()
        self.connect_button.hide()
        self.status.setText("Connecting…")
        self.process = QProcess(self)
        process = self.process
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("SCREEN_SHARING_CTRL_AS_CMD", "1" if self.profile.ctrl_as_cmd else "0")
        env.insert("SCREEN_SHARING_GRAB_KEYBOARD", "1" if self.profile.grab_keyboard else "0")
        env.insert("SCREEN_SHARING_APP_ID", f"screen-sharing-{self.profile.id}")
        env.insert("SCREEN_SHARING_MACHINE", self.profile.machine)
        # Qt may inject its library/plugin paths; the viewer owns GLFW, not Qt.
        for key in ("QT_QPA_PLATFORM_PLUGIN_PATH", "QT_QPA_FONTDIR"):
            env.remove(key)
        process.setProcessEnvironment(env)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(self.read_output)
        process.finished.connect(self.process_finished)
        process.errorOccurred.connect(self.process_error)
        process.start(sys.executable, session_arguments(self.profile, None))
        process.write((password + "\n").encode())
        process.closeWriteChannel()
        self.password.clear()

    def read_output(self):
        if not self.process:
            return
        self.output += bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        # Bound partial lines as well as the diagnostic tail.
        self.output = self.output[-32768:]
        lines = self.output.split("\n")
        self.output = lines.pop()
        for line in lines:
            if line == "SCREEN_SHARING_VIEWER_READY":
                self.viewer_ready()
            else:
                self.logs.append(line)

    def viewer_ready(self):
        if self.ready:
            return
        self.ready = True
        self.hide()
        if self.secret is not None:
            try:
                credentials.save(self.profile.id, self.secret)
                profiles = ProfileStore().load()
                ProfileStore().save([replace(p, remember_password=True) if p.id == self.profile.id else p for p in profiles])
            except Exception as error:
                QMessageBox.warning(self, "Password not saved", str(error))
            finally:
                self.secret = None

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.process_finished(1, QProcess.ExitStatus.CrashExit)

    def process_finished(self, code, exit_status):
        self.read_output()
        if self.process:
            self.process.deleteLater()
            self.process = None
        self.secret = None
        if self.cancelled or (code == 0 and self.ready):
            QApplication.instance().quit()
            return
        self.progress.hide()
        self.form.show()
        self.connect_button.show()
        self.connect_button.setText("Retry")
        self.connect_button.setEnabled(False)
        if code == 2:
            message = "Sign-in failed. Check your Mac username and password."
        elif self.ready:
            message = "The connection ended. Enter your password to reconnect."
        else:
            message = "Couldn’t connect. Check that the Mac is reachable and Screen Sharing is enabled."
        self.status.setText(message)
        # Diagnostic text remains local and is available on stderr when run from a terminal.
        if sys.stderr:
            print("\n".join(self.logs), file=sys.stderr)
        self.show()
        self.raise_()
        self.activateWindow()
        self.password.setFocus()

    def reject(self):
        self.cancelled = True
        self.secret = None
        self.password.clear()
        if self.process is not None:
            self.process.terminate()
            process = self.process
            QTimer.singleShot(1500, lambda: process.kill() if self.process is process and process.state() != QProcess.ProcessState.NotRunning else None)
            self.status.setText("Disconnecting…")
        else:
            QApplication.instance().quit()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="screen-sharing --app")
    parser.add_argument("connection")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--fullscreen", action="store_true", default=None)
    mode.add_argument("--windowed", dest="fullscreen", action="store_false")
    args = parser.parse_args(argv)
    app = QApplication.instance() or QApplication(["screen-sharing"])
    app.setApplicationName("Screen Sharing")
    app.theme_controller = ThemeController(app)
    app.setQuitOnLastWindowClosed(False)
    try:
        profile = find(ProfileStore().load(), args.connection)
        if args.fullscreen is not None:
            profile = replace(profile, fullscreen=args.fullscreen)
    except (OSError, ValueError) as error:
        QMessageBox.critical(None, "Screen Sharing", str(error))
        return 1
    app.setDesktopFileName(f"screen-sharing-{profile.id}")
    dialog = SessionDialog(profile)
    dialog.show()
    QTimer.singleShot(0, dialog.autoconnect)
    return app.exec()
