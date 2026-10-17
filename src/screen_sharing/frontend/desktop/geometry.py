"""One aspect-preserving transform for video, cursors, and remote input."""


def fit_viewport(source_w, source_h, target_w, target_h):
    """Centered (x, y, width, height) in target coordinates."""
    if min(source_w, source_h, target_w, target_h) <= 0:
        return (0.0, 0.0, 0.0, 0.0)
    scale = min(target_w / source_w, target_h / source_h)
    width, height = source_w * scale, source_h * scale
    return ((target_w - width) / 2, (target_h - height) / 2, width, height)


def to_canvas(x, y, window_w, window_h, crop):
    """Invert the video transform, clamping edge drags to the remote display."""
    rx, ry, width, height = crop
    vx, vy, vw, vh = fit_viewport(width, height, window_w, window_h)
    if vw <= 0 or vh <= 0:
        return None
    u = min(1.0, max(0.0, (x - vx) / vw))
    v = min(1.0, max(0.0, (y - vy) / vh))
    return (rx + min(width - 1, int(u * width)),
            ry + min(height - 1, int(v * height)))
