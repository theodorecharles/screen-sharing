import pytest
from screen_sharing.frontend.desktop.geometry import fit_viewport, to_canvas


@pytest.mark.parametrize('target', [(700,840),(1440,960),(1900,600)])
def test_picture_keeps_proportions_at_every_window_shape(target):
    x,y,w,h = fit_viewport(1920,1080,*target)
    assert w/h == pytest.approx(1920/1080)
    assert x*2+w == pytest.approx(target[0])
    assert y*2+h == pytest.approx(target[1])
    assert 0 <= x and 0 <= y and w <= target[0] and h <= target[1]


def test_mouse_uses_video_offset_and_monitor_crop_at_hidpi():
    crop = (1920,0,1920,1080)
    for density in (1,1.5,2):
        x,y,w,h = fit_viewport(crop[2],crop[3],700*density,840*density)
        # Physical video points map back through logical mouse coordinates.
        assert to_canvas((x+w*.25)/density,(y+h*.75)/density,700,840,crop) == (2400,810)
        assert to_canvas((x+w*.5)/density,(y+h*.5)/density,700,840,crop) == (2880,540)
    assert to_canvas(350,-50,700,840,crop) == (2880,0)
    assert to_canvas(350,900,700,840,crop) == (2880,1079)


def test_renderer_and_cursor_use_the_centered_viewport():
    from screen_sharing.frontend.desktop.gpu import Renderer
    from types import SimpleNamespace
    import numpy as np
    viewports=[]; buffers=[]
    renderpass = SimpleNamespace(set_pipeline=lambda *a:None,set_bind_group=lambda *a:None,
        set_viewport=lambda *a:viewports.append(a),draw=lambda *a:None,end=lambda:None)
    encoder = SimpleNamespace(begin_render_pass=lambda **kw:renderpass,finish=lambda:None)
    r=Renderer.__new__(Renderer)
    r._device=SimpleNamespace(create_command_encoder=lambda:encoder,
        queue=SimpleNamespace(write_buffer=lambda buf,offset,data:buffers.append(np.frombuffer(data,np.float32)),submit=lambda *a:None))
    r._w,r._h=1920,1080;r._content_w,r._content_h=1920,1080;r._src_rect=None
    r._chroma_ratio=(1.,1.);r._mode='planar';r._uniform_buf=None;r._pipeline_planar=None;r._bind_planar=None
    r._cursor_tex=object();r._cursor_bind_group=object();r._cursor_pos=(960,540)
    r._cur_w,r._cur_h=20,20;r._cur_hx,r._cur_hy=0,0;r._cursor_scale=1
    r._cursor_uniform_buf=None;r._cursor_pipeline=None
    r.draw(None,700,840)
    assert viewports[0][:4] == pytest.approx(fit_viewport(1920,1080,700,840))
    # Pointer at content center must also land at viewport/window center.
    assert buffers[-1][0] == pytest.approx(0)
    assert buffers[-1][1] == pytest.approx(0)
