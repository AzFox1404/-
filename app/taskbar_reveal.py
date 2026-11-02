"""Reveal the real Windows taskbar by clipping our fullscreen window, not resizing it.

No shell settings, Explorer geometry, or auto-hide preferences are changed.
Only runs while the bottom 24px trigger or taskbar is in use.
"""
import ctypes as C
from ctypes import wintypes as W
import time


def install(root):
    if getattr(root,'taskbar_reveal',None):return
    u=C.windll.user32;g=C.windll.gdi32
    u.GetParent.argtypes=[W.HWND];u.GetParent.restype=W.HWND
    u.FindWindowW.argtypes=[W.LPCWSTR,W.LPCWSTR];u.FindWindowW.restype=W.HWND
    u.GetWindowRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
    u.GetForegroundWindow.restype=W.HWND
    u.SetWindowRgn.argtypes=[W.HWND,W.HRGN,W.BOOL]
    g.CreateRectRgn.argtypes=[C.c_int]*4;g.CreateRectRgn.restype=W.HRGN
    g.DeleteObject.argtypes=[W.HGDIOBJ]
    hwnd=u.GetParent(root.winfo_id()) or root.winfo_id()
    state={'height':0,'bar':None,'timer':None,'frame':None,'target':0}
    root.taskbar_reveal=state

    def region(height):
        if not height:u.SetWindowRgn(hwnd,None,True);return
        rect=W.RECT();u.GetWindowRect(hwnd,C.byref(rect))
        handle=g.CreateRectRgn(0,0,rect.right-rect.left,max(1,rect.bottom-rect.top-height))
        if not u.SetWindowRgn(hwnd,handle,True):g.DeleteObject(handle)

    def reset(event=None):
        if event is not None and event.widget is not root:return
        for key in ('timer','frame'):
            if state[key] is not None:root.after_cancel(state[key]);state[key]=None
        if state['height']:region(0)
        state.update(height=0,target=0,bar=None)

    def animate(target):
        if not target and not state['height'] and state['frame'] is None:reset();return
        if state['target']==target:return
        state['target']=target
        if state['frame'] is not None:root.after_cancel(state['frame'])
        start=state['height'];began=time.monotonic()
        def frame():
            state['frame']=None
            t=min(1,(time.monotonic()-began)/.20);ease=t*t*(3-2*t)
            state['height']=round(start+(target-start)*ease);region(state['height'])
            if t<1:state['frame']=root.after(16,frame)
            elif not target:reset()
        frame()

    def poll():
        state['timer']=None
        if not root.winfo_exists():return
        if not root.attributes('-fullscreen') or not root.winfo_viewable():reset();return
        bar=state['bar'];rect=W.RECT();point=W.POINT()
        u.GetWindowRect(hwnd,C.byref(rect));u.GetCursorPos(C.byref(point))
        bar_rect=W.RECT()
        if not bar or not u.GetWindowRect(bar,C.byref(bar_rect)):reset();return
        foreground=u.GetForegroundWindow()
        inside=rect.left<=point.x<rect.right and min(rect.bottom-24,bar_rect.top)<=point.y<rect.bottom
        if foreground not in (hwnd,bar) or not inside:animate(0)
        else:animate(max(0,rect.bottom-bar_rect.top))
        if state['bar']:state['timer']=root.after(70,poll)

    def motion(event):
        nonlocal hwnd
        if state['bar'] or not root.attributes('-fullscreen'):return
        if event.y_root<root.winfo_rooty()+root.winfo_height()-24:return
        # Tk may replace its native wrapper when changing fullscreen styles.
        hwnd=u.GetParent(root.winfo_id()) or root.winfo_id()
        bar=u.FindWindowW('Shell_TrayWnd',None);r=W.RECT()
        if not bar or not u.GetWindowRect(bar,C.byref(r)):return
        # Only the taskbar on this screen, attached to its bottom edge.
        bounds=W.RECT();u.GetWindowRect(hwnd,C.byref(bounds))
        if r.top<bounds.top or r.top>=bounds.bottom or r.bottom<bounds.bottom-4:return
        state['bar']=bar
        # The clipped application exposes the existing taskbar; keep its z-order
        # unchanged so the reveal is progressive instead of instantly popping up.
        poll()
    root.bind_all('<Motion>',motion,add='+')
    root.bind('<Unmap>',reset,add='+');root.bind('<Destroy>',reset,add='+')
    state['reset']=reset
