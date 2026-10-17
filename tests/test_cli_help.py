"""CLI help must survive argparse's percent-style interpolation."""
from __future__ import annotations

from screen_sharing.cli import _make_parser


def test_cli_help_formats_without_interpolation_errors():
    help_text = _make_parser().format_help()

    assert "Ctrl+Alt+Enter" in help_text
    assert "--fullscreen" in help_text
