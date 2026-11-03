"""Drag ghost follows mouse and is removed on drop/cancellation without capture."""
import tempfile,tkinter as tk
from tkinter import ttk
from pathlib import Path
import studio

with tempfile.TemporaryDirectory() as td:
 p=Path(td);studio.STORE=p;studio.PROJECTS=p/'Проекты';studio.LIB=p/'Библиотека/Шаблоны';studio.SAMPLES=p/'missing/sample'
 root=tk.Tk();app=studio.Studio(root);top=tk.Toplevel(root);tree=ttk.Treeview(top);tree.pack()
 source=p/'a.txt';source.write_text('original');dest=p/'folder';dest.mkdir()
 a=tree.insert('','end',text='a.txt',values=(str(source),));b=tree.insert('','end',text='folder',values=(str(dest),))
 calls=[];app.perform_file_operation=lambda *args:calls.append(args);app.folder_drag(tree);root.update()
 def drag():
  y=tree.bbox(a)[1]+8;x=tree.winfo_rootx();sy=tree.winfo_rooty()
  tree.event_generate('<ButtonPress-1>',x=10,y=y,rootx=x+10,rooty=sy+y)
  tree.event_generate('<B1-Motion>',x=50,y=y,rootx=x+50,rooty=sy+y);root.update()
  ghost=tree.drag_ghost
  assert ghost.winfo_viewable() and abs(ghost.attributes('-alpha')-.65)<.01
  assert root.grab_current() is None
  return ghost
 ghost=drag();y=tree.bbox(b)[1]+8
 tree.event_generate('<ButtonRelease-1>',x=10,y=y);root.update()
 assert calls==[(source,'move',dest/source.name)] and not ghost.winfo_exists()
 for event in ('<Escape>','<FocusOut>','<Unmap>'):
  ghost=drag();tree.event_generate(event);root.update();assert not ghost.winfo_exists()
 assert len(calls)==1 and source.read_text()=='original'
 app.toggle_theme(1);root.update();assert root.caption_theme['dark'] and root.caption_theme['dark_mode']
 app.toggle_theme(0);root.update();assert not root.caption_theme['dark']
 ghost=drag();tree.destroy();root.update();assert not ghost.winfo_exists()
 root.destroy();print('PASS translucent ghost, mouse drop, Escape/focus/unmap/destroy cleanup, no capture, native caption themes')
