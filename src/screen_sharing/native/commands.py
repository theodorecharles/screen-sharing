"""Small CLI for saving Macs and creating direct desktop launchers."""
import argparse
from dataclasses import replace
import getpass
import sys

from .profiles import Profile, ProfileStore
from . import credentials, shortcuts


def find(profiles, query):
    matches = [p for p in profiles if p.id == query or p.name.casefold() == query.casefold()]
    if len(matches) != 1:
        raise ValueError(f"Connection {query!r} not found. Run screen-sharing list.")
    return matches[0]


def parser():
    p = argparse.ArgumentParser(prog="screen-sharing", description="Native Mac screen sharing. Save a Mac, create its launcher, connect.",
        epilog="Viewer keys: Ctrl+Alt+Enter = fullscreen; Ctrl+Alt+Escape = disconnect.\nFor low-level session options: screen-sharing session --help.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command")
    for verb, help_text in [("add", "save a Mac"), ("edit", "change a saved Mac")]:
        a = sub.add_parser(verb, help=help_text)
        a.add_argument("name", help="connection name (or ID when editing)")
        a.add_argument("--host", required=verb == "add")
        a.add_argument("--user", dest="username", required=verb == "add")
        a.add_argument("--rename", dest="new_name")
        a.add_argument("--port", type=int)
        a.add_argument("--machine", choices=("mac-mini", "mac-studio"))
        mode = a.add_mutually_exclusive_group()
        mode.add_argument("--fullscreen", dest="fullscreen", action="store_true", default=None)
        mode.add_argument("--windowed", dest="fullscreen", action="store_false")
        for flag in ("audio", "curtain", "ctrl-as-cmd", "grab-keyboard"):
            a.add_argument("--" + flag, action=argparse.BooleanOptionalAction, default=None)
        a.add_argument("--resolution", choices=("auto", "1920x1080", "2560x1440", "3840x2160"))
        a.add_argument("--scale", choices=("auto", "on", "off"))
        a.add_argument("--codec", choices=("auto", "hevc", "avc"))
        a.add_argument("--shortcut", action="store_true", help="create an Omarchy application launcher")
    sub.add_parser("list", help="list saved connections")
    for verb, help_text in [("shortcut", "create or refresh a Mac's app launcher"), ("remove", "remove a connection and its launcher"),
                            ("password", "save a password in the system keyring"), ("connect", "open a saved Mac")]:
        a = sub.add_parser(verb, help=help_text)
        a.add_argument("name")
        if verb == "password":
            a.add_argument("--forget", action="store_true")
        if verb == "connect":
            mode = a.add_mutually_exclusive_group()
            mode.add_argument("--fullscreen", action="store_true", default=None)
            mode.add_argument("--windowed", dest="fullscreen", action="store_false")
    sub.add_parser("session", help="direct connection and advanced viewer options", add_help=False)
    return p


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "session":
        from ..cli import main as session
        return session(argv[1:])
    p = parser()
    args = p.parse_args(argv)
    if not args.command:
        p.print_help()
        return 0
    store = ProfileStore()
    try:
        profiles = store.load()
        if args.command == "list":
            if not profiles:
                print("No saved Macs. Use screen-sharing add --help.")
            for profile in profiles:
                print(f"{profile.name}\t{profile.username}@{profile.host}\t{profile.machine}\t{'fullscreen' if profile.fullscreen else 'windowed'}")
            return 0
        if args.command in ("add", "edit"):
            profile = replace(Profile.new(), name=args.name) if args.command == "add" else find(profiles, args.name)
            updates = {field: getattr(args, field) for field in ("host", "username", "port", "machine", "fullscreen", "audio", "curtain", "ctrl_as_cmd", "grab_keyboard", "resolution", "scale", "codec") if getattr(args, field) is not None}
            if args.new_name:
                updates["name"] = args.new_name
            updated = replace(profile, **updates)
            updated.validate()
            if any(other.id != updated.id and other.name.casefold() == updated.name.casefold() for other in profiles):
                raise ValueError("That connection name is already in use.")
            profiles = [other for other in profiles if other.id != updated.id] + [updated]
            store.save(profiles)
            print(f"Saved {updated.name}.")
            if args.shortcut or shortcuts.shortcut_path(updated).exists():
                print(f"App launcher: {shortcuts.create(updated)}")
            return 0
        profile = find(profiles, args.name)
        if args.command == "shortcut":
            print(shortcuts.create(profile))
        elif args.command == "remove":
            credentials.remove(profile.id)
            shortcuts.remove(profile)
            store.save([other for other in profiles if other.id != profile.id])
            print(f"Removed {profile.name}.")
        elif args.command == "password":
            if args.forget:
                credentials.remove(profile.id)
            else:
                password = getpass.getpass(f"Password for {profile.username}@{profile.host}: ")
                if not password:
                    raise ValueError("Password cannot be empty.")
                credentials.save(profile.id, password)
            store.save([replace(other, remember_password=not args.forget) if other.id == profile.id else other for other in profiles])
            print("Password forgotten." if args.forget else "Password saved in the system keyring.")
        elif args.command == "connect":
            from .session import main as launch
            options = [profile.id]
            if args.fullscreen is not None:
                options += ["--fullscreen" if args.fullscreen else "--windowed"]
            return launch(options)
        return 0
    except (ValueError, OSError, RuntimeError, credentials.keyring.errors.KeyringError) as error:
        print(f"Screen Sharing: {error}", file=sys.stderr)
        return 1
