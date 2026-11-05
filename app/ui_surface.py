"""Native repaint and client-frame geometry, without capturing the desktop."""
import ctypes as C
from ctypes import wintypes as W

def repaint(widget, immediate=True):
    if not widget.winfo_exists():return
    u=C.windll.user32
    u.RedrawWindow.argtypes=[W.HWND,C.c_void_p,W.HRGN,W.UINT]
    u.RedrawWindow(widget.winfo_id(),None,None,0x85 | (0x100 if immediate else 0)) # invalidate, erase, all children

def install_repaint(canvas):
    if getattr(canvas,'repaint_installed',False):return
    canvas.repaint_installed=True;pending=[None];painting=[False];last=[None]
    def clip_children(event=None):
        if event is not None and event.widget is not canvas:return
        u=C.windll.user32
        u.GetWindowLongPtrW.argtypes=[W.HWND,C.c_int];u.GetWindowLongPtrW.restype=C.c_ssize_t
        u.SetWindowLongPtrW.argtypes=[W.HWND,C.c_int,C.c_ssize_t]
        handle=canvas.winfo_id()
        u.SetWindowLongPtrW(handle,-16,u.GetWindowLongPtrW(handle,-16)|0x02000000|0x04000000)
    canvas.bind('<Map>',clip_children,add='+')
    def schedule(*args):
        if painting[0]:return
        current=(canvas.xview(),canvas.yview(),canvas.winfo_width(),canvas.winfo_height())
        if current==last[0]:return
        last[0]=current
        if pending[0] is None:pending[0]=canvas.after(16,flush)
    def flush():
        pending[0]=None;painting[0]=True
        try:repaint(canvas, immediate=False)
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
        def sizing_edge(event):
            if window.attributes('-fullscreen') or window.state()=='zoomed':return
            x=event.x_root-window.winfo_rootx();y=event.y_root-window.winfo_rooty()
            width=window.winfo_width();height=window.winfo_height()
            if not (0<=x<width and 0<=y<height):return
            horizontal,vertical=map(int,window.resizable())
            left,right=x<6,x>=width-6
            top,bottom=y<6,y>=height-6
            edge=None
            if horizontal and vertical:
                if x<20 and y<20 and (left or top):edge=4
                elif x>=width-20 and y<20 and (right or top):edge=5
                elif x<20 and y>=height-20 and (left or bottom):edge=7
                elif x>=width-20 and y>=height-20 and (right or bottom):edge=8
            if edge is None:
                if horizontal and (left or right):edge=1 if left else 2
                elif vertical and (top or bottom):edge=3 if top else 6
                else:return
            return edge
        def resize(event):
            edge=sizing_edge(event)
            if edge is None:return
            handle=u.GetParent(window.winfo_id()) or window.winfo_id()
            u.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM]
            u.PostMessageW.restype=W.BOOL
            u.ReleaseCapture();u.PostMessageW(handle,0x112,0xF000+edge,0)
            return 'break'
        # Run before a child handles the press (e.g. caption move or a ttk button).
        tag=f'FrameResize:{window}'
        cursors={1:'size_we',2:'size_we',3:'size_ns',6:'size_ns',
                 4:'size_nw_se',8:'size_nw_se',5:'size_ne_sw',7:'size_ne_sw'}
        hovered=None
        saved_cursor=None
        def leave(event=None):
            nonlocal hovered
            if hovered is not None and hovered.winfo_exists():hovered.configure(cursor=saved_cursor)
            hovered=None
        def motion(event):
            nonlocal hovered,saved_cursor
            edge=sizing_edge(event)
            if hovered is not event.widget or edge is None:leave()
            if edge is not None:
                if hovered is None:
                    saved_cursor=event.widget.cget('cursor')
                    hovered=event.widget
                if hovered.cget('cursor')!=cursors[edge]:hovered.configure(cursor=cursors[edge])
        bindings={'<ButtonPress-1>':resize,'<Motion>':motion,'<Leave>':leave}
        for sequence,callback in bindings.items():window.bind_class(tag,sequence,callback)
        def attach(widget):
            tags=widget.bindtags()
            if tag not in tags:widget.bindtags((tag,*tags))
        def dispose(event):
            if event.widget is window:
                for sequence in bindings:window.unbind_class(tag,sequence)
        window.bind('<Map>',lambda event:attach(event.widget),add='+')
        window.bind('<Destroy>',dispose,add='+')
        stack=[window]
        while stack:
            widget=stack.pop();attach(widget)
            stack.extend(w for w in widget.winfo_children() if w.winfo_toplevel() is window)
        window._frame_resize_bound=True
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
        if u.SetWindowRgn(hwnd,region,True):repaint(window,immediate=False)
        else:g.DeleteObject(region)

def transition(window,action):
    """Coalesce native window geometry changes into one repaint."""
    try:action()
    finally:window.after_idle(lambda:repaint(window,immediate=False))

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
