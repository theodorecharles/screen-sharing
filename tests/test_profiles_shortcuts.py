from dataclasses import replace
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

from screen_sharing.native.profiles import Profile, ProfileStore, session_arguments
from screen_sharing.native import commands, shortcuts


def profile(**kw):
    return replace(Profile(str(uuid4()), "My Mac", "mac.local", "ted"), **kw)


def test_private_roundtrip_and_password_not_in_config(tmp_path):
    store = ProfileStore(tmp_path / "settings/connections.json")
    saved = profile(fullscreen=True, machine="mac-studio")
    store.save([saved])
    assert store.load() == [saved]
    assert store.path.stat().st_mode & 0o777 == 0o600
    assert store.path.parent.stat().st_mode & 0o777 == 0o700
    document = json.loads(store.path.read_text())
    document['connections'][0]['password'] = 'never-persist'
    store.path.write_text(json.dumps(document))
    store.save(store.load())
    assert 'never-persist' not in store.path.read_text()
    args = session_arguments(saved, None)
    assert '--password-stdin' in args and '--fullscreen' in args
    assert None not in args and '--control-socket' not in args


@pytest.mark.parametrize('change', [{'id':'../../evil'}, {'name':'a\nExec=bad'}, {'host':'--headless'}, {'host':'https://mac.local'}, {'username':13}, {'port':0}, {'machine':'../bad'}, {'fullscreen':'yes'}])
def test_malformed_profile_rejected(change):
    with pytest.raises((ValueError, TypeError)):
        profile(**change).validate()


def test_bad_config_is_preserved_on_command(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    path = tmp_path / 'screen-sharing/connections.json'
    path.parent.mkdir()
    path.write_text('broken')
    assert commands.main(['add','New','--host','mac.local','--user','ted']) == 1
    assert path.read_text() == 'broken'


def test_add_edit_shortcut_and_remove(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / 'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path / 'data'))
    monkeypatch.setattr(commands.credentials, 'remove', lambda _: None)
    monkeypatch.setattr(shortcuts, 'refresh', lambda: None)
    assert commands.main(['add','Mac Studio','--host','studio.local','--user','ted','--machine','mac-studio','--shortcut']) == 0
    saved = ProfileStore().load()[0]
    entry = shortcuts.shortcut_path(saved)
    text = entry.read_text()
    assert 'Name=Mac Studio\n' in text
    assert 'Terminal=false' in text
    assert '--app' in text and saved.id in text
    assert 'studio.local' not in text and 'password' not in text
    assert '[Desktop Action Fullscreen]' in text
    assert commands.main(['edit','Mac Studio','--rename','Studio','--fullscreen']) == 0
    assert ProfileStore().load()[0].fullscreen
    assert 'Name=Studio\n' in entry.read_text()
    assert commands.main(['remove','Studio']) == 0
    assert not entry.exists() and ProfileStore().load() == []


def test_exec_argument_escapes_desktop_metacharacters():
    escaped = shortcuts.exec_argument('/space dir/$HOME/"quote"/100%/`cmd`')
    assert escaped.startswith('"/space dir/') and escaped.endswith('"')
    assert '100%%' in escaped
    assert '\\\\$HOME' in escaped and '\\\\`cmd\\\\`' in escaped
