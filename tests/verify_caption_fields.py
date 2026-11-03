"""Repeated themes, custom caption lifecycle, real Entry/Combobox editing."""
import tempfile,tkinter as tk
from tkinter import ttk,font
from pathlib import Path
import studio
import ctypes as C
from ctypes import wintypes as W

with tempfile.TemporaryDirectory() as td:
 p=Path(td);studio.STORE=p;studio.PROJECTS=p/'Проекты';studio.LIB=p/'Библиотека/Шаблоны';studio.SAMPLES=p/'missing/sample'
 root=tk.Tk();app=studio.Studio(root);errors=[];root.report_callback_exception=lambda *e:errors.append(str(e[1]))
 win=tk.Toplevel(root);win.title('Dialog');entry=ttk.Entry(win);entry.pack();combo=ttk.Combobox(win,values=('Первый','Второй'));combo.pack()
 for dark in (1,0,1,0,1):
  app.toggle_theme(dark);root.update()
  for window in (root,win):
   bar=window.app_caption
   assert bar.winfo_exists() and bar.cget('background')==app.colors['accent']
   assert bar.label.cget('foreground')==app.colors['text']
   assert len([c for c in window.winfo_children() if getattr(c,'native_caption',False)])==1
   assert bar.logo.cget('image') and bar.feather
   bar.buttons[0].event_generate('<Enter>');root.update();assert 'active' in bar.buttons[0].state()
   bar.buttons[0].event_generate('<Leave>')
   u=C.windll.user32;u.GetClientRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
   hwnd=u.GetParent(window.winfo_id()) or window.winfo_id();outer=W.RECT();client=W.RECT()
   u.GetWindowRect(hwnd,C.byref(outer));u.GetClientRect(hwnd,C.byref(client))
   assert not getattr(window,'_client_proc',None),'native message dispatch must not enter a Python callback'
   assert window._client_bounds[2:]==(client.right,client.bottom)
   g=C.windll.gdi32;g.CreateRectRgn.argtypes=[C.c_int]*4;g.CreateRectRgn.restype=W.HRGN
   u.GetWindowRgn.argtypes=[W.HWND,W.HRGN];g.GetRgnBox.argtypes=[W.HRGN,C.POINTER(W.RECT)]
   region=g.CreateRectRgn(0,0,0,0);box=W.RECT();assert u.GetWindowRgn(hwnd,region)>0;g.GetRgnBox(region,C.byref(box));g.DeleteObject(region)
   ix,iy,iw,ih=window._client_bounds;assert (box.left,box.top,box.right,box.bottom)==(ix,iy,ix+iw,iy+ih),('white frame must be outside visible region',(box.left,box.top,box.right,box.bottom),(ix,iy,ix+iw,iy+ih))
  for w in (entry,combo):assert font.Font(root=root,font=w.cget('font')).actual('family')=='Times New Roman'
  assert entry.cget('style')=='Form.TEntry' and combo.cget('style')=='Form.TCombobox'
  entry.delete(0,'end');entry.insert(0,'Текст 123');entry.selection_range(0,5);assert entry.selection_present()
  combo.current(1);assert combo.get()=='Второй'
 root.title('New title');assert root.app_caption.label.cget('text')=='New title'
 closed=[];win.protocol('WM_DELETE_WINDOW',lambda:closed.append(True));win.app_caption.buttons[0].invoke();assert closed==[True]
 app.toggle_fullscreen();root.update();assert not root.app_caption.winfo_manager()
 app.toggle_fullscreen();root.update();assert root.app_caption.winfo_manager()=='pack'
 assert not root.attributes('-topmost')
 root.destroy();assert not errors,errors
 print('PASS repeated caption palettes/title/close/fullscreen and Times New Roman editable rounded Entry/Combobox')
