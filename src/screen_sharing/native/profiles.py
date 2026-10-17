"""Saved connections. Credentials never enter the profile document."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json
import os
from pathlib import Path
import tempfile
from uuid import UUID, uuid4


@dataclass
class Profile:
    id: str
    name: str
    host: str
    username: str
    port: int = 5900
    fullscreen: bool = False
    audio: bool = True
    curtain: bool = False
    resolution: str = "auto"
    scale: str = "auto"
    codec: str = "auto"
    ctrl_as_cmd: bool = True
    grab_keyboard: bool = False
    remember_password: bool = False
    machine: str = "mac-mini"

    @classmethod
    def new(cls):
        return cls(str(uuid4()), "", "", "")

    def validate(self):
        if not isinstance(self.id, str) or str(UUID(self.id)) != self.id:
            raise ValueError("Invalid connection identifier")
        for value in (self.name, self.host, self.username):
            if not isinstance(value, str) or any(ord(c) < 32 or ord(c) == 127 for c in value):
                raise ValueError("Connection fields must be text without control characters.")
        self.name = self.name.strip()
        self.host = self.host.strip()
        self.username = self.username.strip()
        if not self.name or not self.host or not self.username:
            raise ValueError("Enter a name, Mac address, and username.")
        if any(c.isspace() for c in self.host) or "://" in self.host or "/" in self.host:
            raise ValueError("Enter a hostname or IP address, without a URL or path.")
        if self.host.startswith("-") or self.username.startswith("-"):
            raise ValueError("Addresses and usernames cannot start with a dash.")
        if self.machine not in ("mac-mini", "mac-studio"):
            raise ValueError("Machine must be mac-mini or mac-studio.")
        if not isinstance(self.port, int) or not 1 <= self.port <= 65535:
            raise ValueError("Port must be between 1 and 65535.")
        if self.resolution not in ("auto", "1920x1080", "2560x1440", "3840x2160"):
            raise ValueError("Choose a supported display resolution.")
        if self.scale not in ("auto", "off", "on") or self.codec not in ("auto", "hevc", "avc"):
            raise ValueError("Choose supported display settings.")
        for field in ("fullscreen", "audio", "curtain", "ctrl_as_cmd", "grab_keyboard", "remember_password"):
            if not isinstance(getattr(self, field), bool):
                raise ValueError(f"Invalid setting: {field}")


class ProfileStore:
    def __init__(self, path: Path | None = None):
        self.path = path or Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "screen-sharing" / "connections.json"

    def load(self) -> list[Profile]:
        if not self.path.exists():
            return []
        try:
            document = json.loads(self.path.read_text())
            if document.get("version") != 1 or not isinstance(document.get("connections"), list):
                raise ValueError("Unsupported connection-file format")
            names = {f.name for f in fields(Profile)}
            profiles = [Profile(**{k: v for k, v in item.items() if k in names}) for item in document["connections"]]
            for profile in profiles:
                profile.validate()
            if len({p.id for p in profiles}) != len(profiles):
                raise ValueError("Duplicate connection identifiers")
            return profiles
        except (ValueError, TypeError, AttributeError, KeyError) as error:
            raise ValueError(f"Could not read saved connections at {self.path}: {error}") from error

    def save(self, profiles: list[Profile]):
        for profile in profiles:
            profile.validate()
        if len({p.id for p in profiles}) != len(profiles):
            raise ValueError("Duplicate connection identifiers")
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        data = json.dumps({"version": 1, "connections": [asdict(p) for p in profiles]}, indent=2) + "\n"
        fd, temporary = tempfile.mkstemp(dir=self.path.parent, prefix=".connections-")
        try:
            with os.fdopen(fd, "w") as out:
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def session_arguments(profile: Profile, control_socket: str | None) -> list[str]:
    """The password is sent over stdin, never in argv or the environment."""
    args = ["-m", "screen_sharing", "--host", profile.host, "--user", profile.username,
            "--port", str(profile.port), "--password-stdin",
            f"--window-title={profile.name} — Screen Sharing", "--hidpi", profile.scale,
            "--codec", profile.codec, "--audio" if profile.audio else "--no-audio",
            "--curtain" if profile.curtain else "--no-curtain"]
    if control_socket:
        args += ["--control-socket", control_socket]
    if profile.resolution != "auto":
        args += ["--advertise", profile.resolution]
    if profile.fullscreen:
        args.append("--fullscreen")
    return args
