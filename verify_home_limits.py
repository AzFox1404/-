import tempfile,tkinter as tk
from pathlib import Path
import studio
with tempfile.TemporaryDirectory() as td:
 studio.STORE=Path(td)/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека'/'Шаблоны'
 root=tk.Tk();app=studio.Studio(root);errors=[]
 root.report_callback_exception=lambda *e:errors.append(str(e[1]))
 root.update()
 panes,left,right,center=app.home_layout
 for width in (1380,1100,950):
  root.geometry(f'{width}x820');root.update()
  panes.sash_place(0,1200,0);panes.event_generate('<ButtonRelease-1>',x=1200,y=20);root.update()
  print('WIDTH',root.winfo_width(),'MIN',root.minsize(),'LEFT',left.winfo_width(),'RIGHT',right.winfo_width(),'CENTER',center.winfo_width(),flush=True)
  assert center.winfo_width()>=340
  for child in center.winfo_children():
   assert child.winfo_width()<=center.winfo_width()
  for child in right.winfo_children():
   assert child.winfo_x()>=0 and child.winfo_x()+child.winfo_width()<=right.winfo_width()
 assert not errors,errors
 from PIL import ImageGrab
 root.geometry('1380x820');root.update()
 panes.sash_place(0,1200,0);panes.event_generate('<ButtonRelease-1>',x=1200,y=20);root.update()
 Path('review').mkdir(exist_ok=True)
 x,y=root.winfo_rootx(),root.winfo_rooty()
 ImageGrab.grab((x,y,x+root.winfo_width(),y+root.winfo_height())).save('review/home-width-limits.png')
 app.close()
 print('PASS home splitter reserves readable creation and quality blocks',flush=True)
