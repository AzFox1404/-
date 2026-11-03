"""Native repaint and client-frame geometry, without capturing the desktop."""
import ctypes as C
from ctypes import wintypes as W

def repaint(widget):
    if not widget.winfo_exists():return
    u=C.windll.user32
    u.RedrawWindow.argtypes=[W.HWND,C.c_void_p,W.HRGN,W.UINT]
    u.RedrawWindow(widget.winfo_id(),None,None,0x185) # invalidate, erase, all children, now

def install_repaint(canvas):
    if getattr(canvas,'repaint_installed',False):return
    canvas.repaint_installed=True;pending=[None];painting=[False];last=[None]
    def schedule(*args):
        if painting[0]:return
        current=(canvas.xview(),canvas.yview(),canvas.winfo_width(),canvas.winfo_height())
        if current==last[0]:return
        last[0]=current
        if pending[0] is None:pending[0]=canvas.after(16,flush)
    def flush():
        pending[0]=None;painting[0]=True
        try:repaint(canvas)
        finally:painting[0]=False
    def cancel(e):
        if e.widget is canvas and pending[0] is not None:
            canvas.after_cancel(pending[0]);pending[0]=None
    canvas.bind('<Configure>',schedule,add='+');canvas.bind('<Destroy>',cancel,add='+')
    canvas.repaint_after_scroll=schedule
    return schedule

def rounded_frame(window):
    """Clip the non-client frame; leave native client-size calculations intact."""
    u=C.windll.user32;g=C.windll.gdi32
    u.GetParent.argtypes=[W.HWND];u.GetParent.restype=W.HWND
    hwnd=u.GetParent(window.winfo_id())
    if not hwnd or not window.winfo_ismapped():return
    # DWM otherwise paints a separate rectangular frame/shadow outside
    # the rounded GDI region on Windows 10.
    if getattr(window,'_unframed_hwnd',None)!=hwnd:
        attribute=C.windll.dwmapi.DwmSetWindowAttribute
        attribute.argtypes=[W.HWND,W.DWORD,C.c_void_p,W.DWORD]
        policy=C.c_int(1)  # DWMNCRP_DISABLED
        attribute(hwnd,2,C.byref(policy),C.sizeof(policy))
        window._unframed_hwnd=hwnd
    u.GetWindowRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
    u.IsZoomed.argtypes=[W.HWND]
    u.SetWindowPos.argtypes=[W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT]
    # Never subclass Tk's HWND with a Python WndProc. The wrapper can be
    # destroyed/recreated inside a native message; a collected callback there
    # is a process crash, not a recoverable Tk exception.
    if not getattr(window,'_frame_resize_bound',False):
        def resize(event):
            if window.attributes('-fullscreen') or window.state()=='zoomed':return
            x=event.x_root-window.winfo_rootx();y=event.y_root-window.winfo_rooty()
            width=window.winfo_width();height=window.winfo_height()
            left=x<5;right=x>=width-5;top=y<5;bottom=y>=height-5
            edge=(4 if left else 5 if right else 3) if top else (7 if left else 8 if right else 6) if bottom else 1 if left else 2 if right else None
            if edge is None:return
            if not any(map(int,window.resizable())):return
            handle=u.GetParent(window.winfo_id()) or window.winfo_id()
            u.SendMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM]
            u.SendMessageW.restype=C.c_ssize_t
            u.ReleaseCapture();u.SendMessageW(handle,0x112,0xF000+edge,0)
            return 'break'
        window.bind('<ButtonPress-1>',resize,add='+');window._frame_resize_bound=True
    u.SetWindowRgn.argtypes=[W.HWND,W.HRGN,W.BOOL]
    r=W.RECT();u.GetWindowRect(hwnd,C.byref(r))
    u.GetClientRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
    u.ClientToScreen.argtypes=[W.HWND,C.POINTER(W.POINT)]
    client=W.RECT();origin=W.POINT();u.GetClientRect(hwnd,C.byref(client));u.ClientToScreen(hwnd,C.byref(origin))
    ix=origin.x-r.left;iy=origin.y-r.top;iw=client.right;ih=client.bottom
    window._client_bounds=(ix,iy,iw,ih)
    signature=(hwnd,r.right-r.left,r.bottom-r.top,ix,iy,iw,ih,bool(window.attributes('-fullscreen')),bool(u.IsZoomed(hwnd)))
    window._frame_full=signature[-2]
    if signature==getattr(window,'_rounded_signature',None):return
    window._rounded_signature=signature
    if window.attributes('-fullscreen') or u.IsZoomed(hwnd):
        if not getattr(window,'taskbar_reveal',{}).get('height'):u.SetWindowRgn(hwnd,None,True)
    else:
        g.CreateRoundRectRgn.argtypes=[C.c_int]*6;g.CreateRoundRectRgn.restype=W.HRGN;g.DeleteObject.argtypes=[W.HGDIOBJ]
        # GDI's rounded region drops its far pixel; +1 reaches the client edge
        # exactly (verified with GetRgnBox), without exposing non-client pixels.
        region=g.CreateRoundRectRgn(ix,iy,ix+iw+1,iy+ih+1,20,20)
        if not u.SetWindowRgn(hwnd,region,True):g.DeleteObject(region)

def transition(window,action):
    """Coalesce native window geometry changes into one repaint."""
    try:action()
    finally:window.after_idle(lambda:repaint(window) if window.winfo_exists() else None)

def restore_client_size(window,geometry):
    """Tk caches the standard caption's border; restore actual client pixels."""
    if not window.winfo_exists() or window.attributes('-fullscreen'):return
    import re
    match=re.match(r'(\d+)x(\d+)',geometry)
    if not match:return
    width,height=map(int,match.groups())
    u=C.windll.user32
    u.GetParent.argtypes=[W.HWND];u.GetParent.restype=W.HWND
    u.GetWindowRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
    u.GetClientRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
    u.SetWindowPos.argtypes=[W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT]
    handle=u.GetParent(window.winfo_id()) or window.winfo_id();outer=W.RECT();client=W.RECT()
    u.GetWindowRect(handle,C.byref(outer));u.GetClientRect(handle,C.byref(client))
    if (width,height)!=(client.right,client.bottom):
        u.SetWindowPos(handle,None,0,0,outer.right-outer.left+width-client.right,
                       outer.bottom-outer.top+height-client.bottom,0x16)
