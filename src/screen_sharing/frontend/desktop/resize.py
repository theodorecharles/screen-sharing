"""Coalesce window changes without treating old server replies as new requests."""
from dataclasses import dataclass


@dataclass
class ResizeTracker:
    debounce: float = .35
    min_interval: float = 1.0
    retry_interval: float = 3.0
    max_attempts: int = 3
    desired: tuple | None = None
    changed_at: float = 0.0
    attempted_at: float = float('-inf')
    attempts: int = 0

    def poll(self, target, scaled, backing, now):
        """Return a request when due. Replies only confirm their own geometry.

        target is logical width/height/scale; scaled/backing are the latest
        host-reported sizes. A delayed reply never changes the desired target.
        Retries are bounded because a Mac may clamp or reject a display mode.
        """
        if target != self.desired:
            self.desired = target
            self.changed_at = now
            self.attempts = 0
        width, height, scale = target
        confirmed = (abs(scaled[0] - width) <= 2 and abs(scaled[1] - height) <= 2
                     and abs(backing[0] - round(width * scale)) <= 2
                     and abs(backing[1] - round(height * scale)) <= 2)
        if confirmed:
            self.attempts = 0
            return None
        if now - self.changed_at < self.debounce or self.attempts >= self.max_attempts:
            return None
        interval = self.retry_interval if self.attempts else self.min_interval
        if now - self.attempted_at < interval:
            return None
        self.attempted_at = now
        self.attempts += 1
        return target
