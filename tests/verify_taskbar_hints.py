"""Native fullscreen clipping, without moving the user's physical mouse."""
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import tempfile,time,tkinter as tk
from tkinter import ttk
import studio

def pump(root,seconds=.3):
    end=time.monotonic()+seconds
    while time.monotonic()<end:root.update();time.sleep(.004)

with tempfile.TemporaryDirectory() as td:
    p=Path(td);studio.STORE=p;studio.PROJECTS=p/'Проекты';studio.LIB=p/'Библиотека/Шаблоны'
    root=tk.Tk();app=studio.Studio(root);errors=[]
    root.report_callback_exception=lambda *e:errors.append(str(e[1]))
    button=ttk.Button(root,text='Сохранить');button.pack();app.paint(root);pump(root)
    assert not getattr(button,'has_hint',False)
    row=tk.Frame(root,bg=app.colors['bg']);row.pack();icon=app.icon_button(row,'save','Сохранить документ',lambda:None);pump(root)
    assert icon.has_hint
    app.toggle_fullscreen();pump(root)
    u=C.windll.user32;g=C.windll.gdi32;hwnd=u.GetParent(root.winfo_id()) or root.winfo_id()
    bar=u.FindWindowW('Shell_TrayWnd',None);r=W.RECT();u.GetWindowRect(hwnd,C.byref(r))
    task=W.RECT();assert u.GetWindowRect(bar,C.byref(task))
    before=(root.winfo_width(),root.winfo_height())
    original_cursor=u.GetCursorPos;original_foreground=u.GetForegroundWindow
    point=[r.left+100,r.bottom-10]
    def cursor(pointer):
        dest=C.cast(pointer,C.POINTER(W.POINT));dest.contents.x=point[0];dest.contents.y=point[1];return True
    try:
        u.GetCursorPos=cursor;u.GetForegroundWindow=lambda:hwnd
        root.event_generate('<Motion>',x=100,y=root.winfo_height()-10,rootx=point[0],rooty=point[1]);pump(root,.5)
        state=root.taskbar_reveal
        assert state['height']==r.bottom-task.top and state['height']>0,state
        assert before==(root.winfo_width(),root.winfo_height()),'must clip, never reflow the application'
        # Simulate the shell promoting its taskbar during an Aero Peek preview.
        u.SetWindowPos(bar,C.c_void_p(-1),0,0,0,0,0x13)
        # Leaving the activation area restores the whole window and stops polling.
        point[1]=r.top+100;pump(root,.5)
        assert state['height']==0 and state['frame'] is None,state
        assert not u.GetWindowLongPtrW(bar,-20)&8,'taskbar must not remain above the active fullscreen app'
        # A click back into the app starts outside the trigger: it must hide a
        # shell-promoted taskbar even without another bottom-edge mouse motion.
        state['reset']();u.SetWindowPos(bar,C.c_void_p(-1),0,0,0,0,0x13)
        root.event_generate('<FocusIn>');pump(root)
        assert not u.GetWindowLongPtrW(bar,-20)&8 and state['height']==0
        # A modal has a different HWND but belongs to the same application.
        dialog=tk.Toplevel(root);dialog.transient(root);dialog.grab_set();pump(root)
        modal_hwnd=u.GetParent(dialog.winfo_id()) or dialog.winfo_id()
        u.GetForegroundWindow=lambda:modal_hwnd;point[1]=r.bottom-10
        dialog.event_generate('<Motion>',x=10,y=10,rootx=point[0],rooty=point[1]);pump(root,.5)
        assert state['height']>0 and dialog.grab_current() is dialog,state
        point[1]=r.top+100;pump(root,.5);assert state['height']==0
        dialog.grab_release();dialog.destroy();u.GetForegroundWindow=lambda:hwnd
        # A fullscreen exit mid-reveal must also clear its native region.
        point[1]=r.bottom-10
        root.event_generate('<Motion>',x=100,y=root.winfo_height()-10,rootx=point[0],rooty=point[1]);pump(root,.12)
        app.toggle_fullscreen();pump(root)
        assert not state['height'] and state['timer'] is None and state['frame'] is None
    finally:
        u.GetCursorPos=original_cursor;u.GetForegroundWindow=original_foreground
    assert not errors,errors
    app.close()
    print('PASS icon-only hints; fullscreen reveal, shell promotion, leave/exit and native stacking; no layout resizing')


