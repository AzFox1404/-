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
        # Leaving the activation area restores the whole window and stops polling.
        point[1]=r.top+100;pump(root,.5)
        assert state['height']==0 and state['timer'] is None and state['frame'] is None,state
        # A fullscreen exit mid-reveal must also clear its native region.
        point[1]=r.bottom-10
        root.event_generate('<Motion>',x=100,y=root.winfo_height()-10,rootx=point[0],rooty=point[1]);pump(root,.12)
        app.toggle_fullscreen();pump(root)
        assert not state['height'] and state['timer'] is None and state['frame'] is None
    finally:
        u.GetCursorPos=original_cursor;u.GetForegroundWindow=original_foreground
    assert not errors,errors
    app.close()
    print('PASS icon-only hints; fullscreen taskbar clip/reveal/leave/exit; no layout resizing or idle polling')


