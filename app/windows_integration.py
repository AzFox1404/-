"""Give each main/undocked window standard resizable Windows taskbar behaviour."""
import ctypes as C
from ctypes import wintypes as W

def theme_caption(window,colors,dark):
    """Native title/frame palette; Windows 10 supports dark/light mode only."""
    if not window.winfo_exists() or window.overrideredirect():return
    u=C.WinDLL('user32');d=C.WinDLL('dwmapi')
    u.GetParent.argtypes=[W.HWND];u.GetParent.restype=W.HWND
    hwnd=u.GetParent(window.winfo_id()) or window.winfo_id()
    d.DwmSetWindowAttribute.argtypes=[W.HWND,W.DWORD,C.c_void_p,W.DWORD]
    def apply(attribute,value):
        data=W.DWORD(value);return d.DwmSetWindowAttribute(hwnd,attribute,C.byref(data),C.sizeof(data))
    def rgb(value):
        value=value.lstrip('#');r,g,b=(int(value[i:i+2],16) for i in (0,2,4));return r|g<<8|b<<16
    mode=apply(20,int(dark))
    if mode:mode=apply(19,int(dark))
    caption=apply(35,rgb(colors['accent']));apply(36,rgb(colors['text']));apply(34,rgb(colors['line']))
    window.caption_theme=dict(dark=dark,native_colors=caption==0,dark_mode=mode==0)

def normal_window(window):
    window.attributes('-topmost',False)
    def apply():
        if not window.winfo_exists() or window.attributes('-fullscreen'):return
        u=C.WinDLL('user32',use_last_error=True)
        u.GetParent.argtypes=[W.HWND];u.GetParent.restype=W.HWND
        get=u.GetWindowLongPtrW;get.argtypes=[W.HWND,C.c_int];get.restype=C.c_ssize_t
        put=u.SetWindowLongPtrW;put.argtypes=[W.HWND,C.c_int,C.c_ssize_t];put.restype=C.c_ssize_t
        hwnd=u.GetParent(window.winfo_id()) or window.winfo_id()
        if not getattr(window,'_fullscreen_owner',False):put(hwnd,-8,0)
        style=get(hwnd,-16)|0x00040000
        style=(style & ~(0x10000|0x20000)) if getattr(window,'_close_only',False) else style|0x10000|0x20000
        put(hwnd,-16,style)
        put(hwnd,-20,(get(hwnd,-20)|0x00040000)&~0x80)
        u.SetWindowPos.argtypes=[W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT]
        u.SetWindowPos(hwnd,C.c_void_p(-2),0,0,0,0,0x33)
    window.after_idle(apply)
    window.bind("<Map>",lambda e:window.after_idle(apply) if e.widget is window else None,add="+")


def monitor_bounds(window):
    u=C.WinDLL('user32',use_last_error=True)
    u.GetParent.argtypes=[W.HWND];u.GetParent.restype=W.HWND
    hwnd=u.GetParent(window.winfo_id()) or window.winfo_id()
    u.MonitorFromWindow.argtypes=[W.HWND,W.DWORD];u.MonitorFromWindow.restype=W.HANDLE
    class INFO(C.Structure):
        _fields_=[('size',W.DWORD),('monitor',W.RECT),('work',W.RECT),('flags',W.DWORD)]
    info=INFO();info.size=C.sizeof(info)
    u.GetMonitorInfoW.argtypes=[W.HANDLE,C.POINTER(INFO)]
    u.GetMonitorInfoW(u.MonitorFromWindow(hwnd,2),C.byref(info));r=info.monitor
    return r.left,r.top,r.right-r.left,r.bottom-r.top

def cover_monitor(window,bounds):
    if not window.winfo_exists() or not window.attributes('-fullscreen'):return
    u=C.WinDLL('user32',use_last_error=True)
    u.GetParent.argtypes=[W.HWND];u.GetParent.restype=W.HWND
    hwnd=u.GetParent(window.winfo_id()) or window.winfo_id()
    get=u.GetWindowLongPtrW;get.argtypes=[W.HWND,C.c_int];get.restype=C.c_ssize_t
    put=u.SetWindowLongPtrW;put.argtypes=[W.HWND,C.c_int,C.c_ssize_t];put.restype=C.c_ssize_t
    put(hwnd,-16,get(hwnd,-16)&~(0x00c00000|0x00040000))
    u.SetWindowPos.argtypes=[W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT]
    u.SetWindowPos(hwnd,None,*bounds,0x0034)

def close_only(window):
    """Keep resizing and the native close action, hide caption min/max boxes."""
    if getattr(window,'_close_only',False):return
    window._close_only=True
    def apply(event=None):
        if event is not None and event.widget is not window:return
        if not window.winfo_exists() or window.overrideredirect():return
        u=C.WinDLL('user32',use_last_error=True)
        u.GetParent.argtypes=[W.HWND];u.GetParent.restype=W.HWND
        get=u.GetWindowLongPtrW;get.argtypes=[W.HWND,C.c_int];get.restype=C.c_ssize_t
        put=u.SetWindowLongPtrW;put.argtypes=[W.HWND,C.c_int,C.c_ssize_t];put.restype=C.c_ssize_t
        hwnd=u.GetParent(window.winfo_id()) or window.winfo_id()
        style=get(hwnd,-16);wanted=style & ~(0x10000|0x20000)
        if style!=wanted:
            put(hwnd,-16,wanted)
            u.SetWindowPos.argtypes=[W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT]
            u.SetWindowPos(hwnd,None,0,0,0,0,0x37)
    window.after_idle(apply);window.bind('<Map>',lambda e:window.after_idle(apply) if e.widget is window else None,add='+')
