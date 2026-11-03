"""Startup without theme toggle, remapped modals, four real native corners."""
import ctypes as C
from ctypes import wintypes as W
import tempfile,time,tkinter as tk
from pathlib import Path
import studio
from app_dialogs import messagebox

def pump(root):
    end=time.monotonic()+.12
    while time.monotonic()<end:root.update();time.sleep(.005)

def frame(window):
    u=C.windll.user32;g=C.windll.gdi32
    u.GetParent.argtypes=[W.HWND];u.GetParent.restype=W.HWND
    u.GetWindowLongPtrW.argtypes=[W.HWND,C.c_int];u.GetWindowLongPtrW.restype=C.c_ssize_t
    u.GetWindowRgn.argtypes=[W.HWND,W.HRGN]
    g.CreateRectRgn.argtypes=[C.c_int]*4;g.CreateRectRgn.restype=W.HRGN
    g.GetRgnBox.argtypes=[W.HRGN,C.POINTER(W.RECT)];g.PtInRegion.argtypes=[W.HRGN,C.c_int,C.c_int];g.DeleteObject.argtypes=[W.HGDIOBJ]
    handle=u.GetParent(window.winfo_id()) or window.winfo_id()
    assert not u.GetWindowLongPtrW(handle,-16)&0xc00000,'system caption returned'
    assert window.app_caption.winfo_ismapped()
    assert not getattr(window,'_client_proc',None)
    region=g.CreateRectRgn(0,0,0,0)
    try:
        assert u.GetWindowRgn(handle,region)>0
        box=W.RECT();g.GetRgnBox(region,C.byref(box));x,y,w,h=window._client_bounds
        assert (box.left,box.top,box.right,box.bottom)==(x,y,x+w,y+h),'nonclient strip exposed'
        for px,py in ((x,y),(x+w-1,y),(x,y+h-1),(x+w-1,y+h-1)):
            assert not g.PtInRegion(region,px,py),'square corner exposed'
        assert g.PtInRegion(region,x+w//2,y+h//2)
    finally:g.DeleteObject(region)

with tempfile.TemporaryDirectory() as td:
    p=Path(td);studio.STORE=p;studio.PROJECTS=p/'Projects';studio.LIB=p/'Library';studio.SAMPLES=p/'none/sample'
    root=tk.Tk();app=studio.Studio(root);errors=[];root.report_callback_exception=lambda *e:errors.append(str(e[1]))
    pump(root);frame(root) # The previous test only checked after toggling theme.
    geometry=root.geometry();app.toggle_fullscreen();pump(root);app.toggle_fullscreen();pump(root)
    assert root.geometry()==geometry,(root.geometry(),geometry)
    frame(root)
    for dark in (True,False):
        app.toggle_theme(dark);pump(root);frame(root)
        for _ in range(3):
            win=tk.Toplevel(root);win.withdraw();win.title('Lifecycle');win.geometry('500x180');tk.Label(win,text='Содержимое').pack()
            app.paint(win);win.transient(root);win.resizable(True,True);win.deiconify();pump(root);frame(win)
            win.withdraw();pump(root);win.deiconify();pump(root);frame(win);win.destroy();pump(root)
        checked=[]
        def finish_modal():
            for win in root.winfo_children():
                if isinstance(win,tk.Toplevel) and win.winfo_viewable():
                    frame(win);checked.append(True);win.app_caption.buttons[0].invoke();return
            root.after(20,finish_modal)
        root.after(100,finish_modal)
        messagebox.showinfo('Сборка','Выберите проект на главной странице.')
        assert checked
    root.destroy();assert not errors,errors
print('PASS startup theme without toggle, 12 modal maps, four rounded corners, no white frame, modal close')
