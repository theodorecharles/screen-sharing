"""Optional OS keyring storage; no file-backed password fallback."""
import keyring

SERVICE = "Screen Sharing"
SYSTEM_BACKENDS = ("keyring.backends.SecretService", "keyring.backends.kwallet",
                   "keyring.backends.libsecret", "keyring.backends.macOS", "keyring.backends.Windows")


def system_backend():
    backend = keyring.get_keyring()
    candidates = getattr(backend, "backends", [backend])
    for candidate in candidates:
        if type(candidate).__module__ in SYSTEM_BACKENDS and candidate.priority > 0:
            return candidate
    return None


def available():
    try:
        return system_backend() is not None
    except Exception:
        return False


def get(profile_id):
    backend = system_backend()
    return backend.get_password(SERVICE, profile_id) if backend else None


def save(profile_id, password):
    backend = system_backend()
    if backend is None:
        raise RuntimeError("A system keyring is unavailable. The password was not saved.")
    backend.set_password(SERVICE, profile_id, password)


def remove(profile_id):
    backend = system_backend()
    if backend:
        try:
            backend.delete_password(SERVICE, profile_id)
        except keyring.errors.PasswordDeleteError:
            pass
