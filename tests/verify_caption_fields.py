"""Repeated themes, custom caption lifecycle, real Entry/Combobox editing."""
import tempfile,tkinter as tk
from tkinter import ttk,font
from pathlib import Path
import studio

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
