from screen_sharing.frontend.desktop.resize import ResizeTracker

A=(1200,800,2)
B=(700,840,2)
C=(720,840,2)


def poll(tracker,target,now,actual=A):
    w,h,scale=actual
    return tracker.poll(target,(w,h),(round(w*scale),round(h*scale)),now)


def test_window_snapped_before_first_poll_still_resizes():
    tracker=ResizeTracker()
    assert poll(tracker,B,0) is None
    assert poll(tracker,B,.4) == B


def test_late_reply_cannot_swallow_newer_window_size():
    tracker=ResizeTracker()
    poll(tracker,B,0)
    assert poll(tracker,B,.4)==B
    assert poll(tracker,C,.5) is None
    # Server only now acknowledges B, while the user wants C.
    assert poll(tracker,C,.9,actual=B) is None
    assert poll(tracker,C,1.5,actual=B)==C
    assert poll(tracker,C,2.,actual=C) is None


def test_small_changes_and_scale_changes_are_not_ignored():
    tracker=ResizeTracker()
    poll(tracker,C,0,actual=B)
    assert poll(tracker,C,.4,actual=B)==C
    target=(720,840,1.5)
    poll(tracker,target,1.,actual=C)
    assert poll(tracker,target,1.5,actual=C)==target


def test_drag_coalesces_to_the_latest_target():
    tracker=ResizeTracker()
    poll(tracker,B,0)
    poll(tracker,C,.2)
    assert poll(tracker,C,.4) is None
    assert poll(tracker,C,.6)==C


def test_unacknowledged_or_failed_requests_retry_but_not_forever():
    tracker=ResizeTracker()
    poll(tracker,B,0)
    assert poll(tracker,B,.4)==B
    assert poll(tracker,B,2.) is None
    assert poll(tracker,B,3.5)==B
    assert poll(tracker,B,6.6)==B
    assert poll(tracker,B,100) is None
    # A new window size starts a new bounded sequence.
    poll(tracker,C,101)
    assert poll(tracker,C,101.4)==C


def test_host_confirmation_stops_retries():
    tracker=ResizeTracker()
    poll(tracker,B,0)
    poll(tracker,B,.4)
    assert poll(tracker,B,10,actual=B) is None
    assert poll(tracker,B,20,actual=B) is None
