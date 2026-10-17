"""Saved-connection commands and the native session viewer."""
import sys


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "--app":
        from .native.session import main as launch
        return launch(args[1:])
    if args and args[0].startswith("-") and args[0] not in ("--help", "-h"):
        from .cli import main as session
        return session(args)
    from .native.commands import main as commands
    return commands(args)
