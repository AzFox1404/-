import tempfile,tkinter as tk,time,ctypes as C
from pathlib import Path
from tkinter import ttk
import studio,resize_preview
from glass_resize import install,capture

def pump(r,n=.2):
 end=time.monotonic()+n
 while time.monotonic()<end:r.update();time.sleep(.01)
with tempfile.TemporaryDirectory() as td:
 p=Path(td);studio.STORE=p;studio.PROJECTS=p/'Проекты';studio.LIB=p/'Библиотека/Шаблоны'
 r=tk.Tk();a=studio.Studio(r);top=tk.Toplevel(r);top.geometry('750x440');split=tk.PanedWindow(top,opaqueresize=False,sashwidth=7);split.pack(fill='both',expand=True)
 for n in range(2):
  f=tk.Frame(split,bg='white');split.add(f,width=350,minsize=200)
  for k in range(7):ttk.Label(f,text='Поле '+str(k)).pack();ttk.Entry(f).pack(fill='x',padx=8,pady=4)
 pump(r);install(split,a)
 u=C.windll.user32;u.GetParent.argtypes=[C.c_void_p];u.GetParent.restype=C.c_void_p;u.GetWindowLongPtrW.argtypes=[C.c_void_p,C.c_int];u.GetWindowLongPtrW.restype=C.c_ssize_t
 hwnd=u.GetParent(top.winfo_id());proc=u.GetWindowLongPtrW(hwnd,-4);resize_preview.install(top);assert u.GetWindowLongPtrW(hwnd,-4)==proc
 im=capture(split.nametowidget(str(split.panes()[0])));assert im and len(im.getcolors(im.width*im.height) or [])>10
 x,y=split.sash_coord(0);split.event_generate('<ButtonPress-1>',x=x+2,y=40);pump(r)
 assert len(split.glass_state['covers'])==1
 for c in split.glass_state['covers']:assert c.winfo_viewable()
 before=split.nametowidget(str(split.panes()[0])).winfo_width()
 split.event_generate('<B1-Motion>',x=x+45,y=40);pump(r)
 assert split.nametowidget(str(split.panes()[0])).winfo_width()==before
 assert int(split.cget('sashwidth'))==3
 overlay=split.glass_state['covers'][0]
 assert (overlay.winfo_x(),overlay.winfo_y(),overlay.winfo_width(),overlay.winfo_height())==(0,0,split.winfo_width(),split.winfo_height())
 assert len(overlay.find_withtag('divider'))==1
 split.event_generate('<ButtonRelease-1>',x=x+45,y=40);pump(r)
 assert not split.glass_state['covers'];assert not split.cget('opaqueresize')
 for offset in (25,-25,35,-35):
  x,y=split.sash_coord(0);split.event_generate('<ButtonPress-1>',x=x+1,y=40);split.event_generate('<B1-Motion>',x=x+offset,y=40)
  split.event_generate('<ButtonRelease-1>',x=x+offset,y=40)
 pump(r)
 assert not any(isinstance(c,tk.Canvas) for c in split.winfo_children()),'retired covers accumulated'
 top.destroy();a.close()
 print('PASS normal native window procedure, one glass capture per pane, visible field boundaries, splitter commit and cover cleanup')
