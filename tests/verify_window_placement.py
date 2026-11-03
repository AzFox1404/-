"""Center utilities/save dialogs in the application, cascade nested windows."""
import tempfile,time,tkinter as tk
from pathlib import Path
import studio

def pump(root):
 end=time.monotonic()+.25
 while time.monotonic()<end:root.update();time.sleep(.005)

with tempfile.TemporaryDirectory() as td:
 p=Path(td);studio.STORE=p;studio.PROJECTS=p/'Проекты';studio.LIB=p/'Библиотека/Шаблоны';studio.SAMPLES=p/'missing/sample'
 root=tk.Tk();app=studio.Studio(root);root.geometry('1400x850+120+80');pump(root)
 for full in (False,True):
  root.attributes('-fullscreen',full);pump(root)
  first=tk.Toplevel(root);first.geometry('500x240');pump(root)
  x=root.winfo_rootx()+(root.winfo_width()-first.winfo_width())//2
  y=root.winfo_rooty()+(root.winfo_height()-first.winfo_height())//2
  assert abs(first.winfo_x()-x)<3 and abs(first.winfo_y()-y)<3,(first.geometry(),x,y)
  second=tk.Toplevel(first);second.geometry('500x240');pump(root)
  assert abs(second.winfo_x()-(x-24))<3 and abs(second.winfo_y()-(y-16))<3
  second.destroy();first.destroy();pump(root)
  answers=[];app.ask_save('Save test',answers.append);pump(root);win=app.decision
  x=root.winfo_rootx()+(root.winfo_width()-win.winfo_width())//2
  y=root.winfo_rooty()+(root.winfo_height()-win.winfo_height())//2
  assert abs(win.winfo_x()-x)<3 and abs(win.winfo_y()-y)<3,(win.geometry(),x,y)
  win.grab_release();win.destroy();app.decision=None
 root.destroy()
 print('PASS centered utility/save dialogs, nested upper-left cascade, normal and fullscreen')
