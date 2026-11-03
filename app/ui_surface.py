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
    hwnd=u.GetParent(window.winfo_id()) or window.winfo_id()
    u.GetWindowLongPtrW.argtypes=[W.HWND,C.c_int];u.GetWindowLongPtrW.restype=C.c_ssize_t
    u.SetWindowLongPtrW.argtypes=[W.HWND,C.c_int,C.c_ssize_t];u.SetWindowLongPtrW.restype=C.c_ssize_t
    u.CallWindowProcW.argtypes=[C.c_void_p,W.HWND,W.UINT,W.WPARAM,W.LPARAM];u.CallWindowProcW.restype=C.c_ssize_t
    u.GetWindowRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
    u.IsZoomed.argtypes=[W.HWND];u.IsWindow.argtypes=[W.HWND]
    u.SetWindowPos.argtypes=[W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT]
    previous=getattr(window,'_client_proc',None)
    if previous and previous[2]!=hwnd:
        cb,prior,handle=previous
        if u.IsWindow(handle) and u.GetWindowLongPtrW(handle,-4)==C.cast(cb,C.c_void_p).value:u.SetWindowLongPtrW(handle,-4,prior)
        window._client_proc=None
    if not getattr(window,'_client_proc',None):
        old=u.GetWindowLongPtrW(hwnd,-4)
        proc_type=C.WINFUNCTYPE(C.c_ssize_t,W.HWND,W.UINT,W.WPARAM,W.LPARAM)
        def proc(handle,msg,wp,lp):
            try:
                if msg==0x84 and not u.IsZoomed(handle) and not getattr(window,'_frame_full',False):
                    r=W.RECT();u.GetWindowRect(handle,C.byref(r));x=C.c_short(lp&65535).value;y=C.c_short((lp>>16)&65535).value
                    ix,iy,iw,ih=getattr(window,'_client_bounds',(0,0,r.right-r.left,r.bottom-r.top))
                    if y<r.top+iy+12:
                        if x<r.left+ix+12:return 13
                        if x>=r.left+ix+iw-12:return 14
                    if y>=r.top+iy+ih-12:
                        if x<r.left+ix+12:return 16
                        if x>=r.left+ix+iw-12:return 17
                    left=x<r.left+ix+3;right=x>=r.left+ix+iw-3;top=y<r.top+iy+3;bottom=y>=r.top+iy+ih-3
                    if top:return 13 if left else 14 if right else 12
                    if bottom:return 16 if left else 17 if right else 15
                    if left:return 10
                    if right:return 11
            except (Exception,):pass
            return u.CallWindowProcW(old,handle,msg,wp,lp)
        callback=proc_type(proc);window._client_proc=(callback,old,hwnd)
        u.SetWindowLongPtrW(hwnd,-4,C.cast(callback,C.c_void_p).value)
        u.SetWindowPos(hwnd,None,0,0,0,0,0x37)
        def dispose(e):
            if e.widget is window and u.IsWindow(hwnd) and u.GetWindowLongPtrW(hwnd,-4)==C.cast(callback,C.c_void_p).value:u.SetWindowLongPtrW(hwnd,-4,old)
        window.bind('<Destroy>',dispose,add='+')
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
