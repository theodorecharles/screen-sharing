from types import SimpleNamespace
from screen_sharing.native import credentials


def test_plaintext_backend_is_never_accepted(monkeypatch):
    class Plaintext:
        priority = 1
    Plaintext.__module__ = 'keyrings.alt.file'
    monkeypatch.setattr(credentials.keyring,'get_keyring',lambda: Plaintext())
    assert not credentials.available()
    monkeypatch.setattr(credentials.keyring,'get_keyring',lambda: SimpleNamespace(backends=[Plaintext()]))
    assert not credentials.available()
