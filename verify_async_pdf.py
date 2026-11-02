from pathlib import Path
import tempfile,time,tkinter as tk
from tkinter import ttk
from reportlab.pdfgen import canvas
import studio
from pdf_page_preview import PagePreview
from test_pdf_wait import wait_pdf
from auto_scroll import install

def pump(r,seconds=.15):
 end=time.monotonic()+seconds
 while time.monotonic()<end:r.update();time.sleep(.003)
with tempfile.TemporaryDirectory() as td:
 p=Path(td);studio.STORE=p;studio.PROJECTS=p/'Проекты';studio.LIB=p/'Библиотека/Шаблоны'
 f=p/'dense.pdf';c=canvas.Canvas(str(f),pagesize=(850,1200))
 for page in range(8):
  c.setFont('Helvetica',7)
  for n in range(150):c.drawString(10,1190-n*7,'Dense PDF text 0123456789 '*6)
  c.showPage()
 c.save();r=tk.Tk();a=studio.Studio(r);top=tk.Toplevel(r);top.geometry('950x700');v=PagePreview(top,a);v.pack(fill='both',expand=True);pump(r)
 samples=[];last=[time.monotonic()];running=[True]
 def heartbeat():
  now=time.monotonic();samples.append(now-last[0]);last[0]=now
  if running[0]:r.after(5,heartbeat)
 r.after(5,heartbeat);t=time.monotonic();v.show(f,0);assert time.monotonic()-t<.05
 wait_pdf(r,v);v.set_zoom(100);wait_pdf(r,v);count=v.renderer.render_count;v.set_zoom(70);wait_pdf(r,v);assert v.renderer.render_count==count
 for zoom in (120,130,140,90):v.set_zoom(zoom)
 wait_pdf(r,v);assert v.zoom==90 and v.renderer.process.poll() is None
 # Middle click scrolling follows pointer distance and stops on click/Escape.
 v.canvas.event_generate('<Button-2>',x=50,y=50);state=v.canvas.auto_scroll_state;assert state['active'];ox,oy=state['origin'];v.canvas.winfo_pointerxy=lambda:(ox,oy+120)
 before=v.canvas.yview()[0];pump(r,.2);assert v.canvas.yview()[0]>before
 v.canvas.event_generate('<Button-2>',x=50,y=50);assert not state['active'] and state['timer'] is None
 v.canvas.event_generate('<Button-2>',x=50,y=50);v.canvas.focus_force();v.canvas.event_generate('<Escape>');pump(r);assert not state['active']
 # A fullscreen modal is owned by the fullscreen root, remains usable, no global topmost.
 a.windows={2:top};a.toggle_fullscreen();pump(r);assert str(top.transient())==str(r);decisions=[];a.ask_save('Проверка',decisions.append);pump(r);dialog=a.decision
 import ctypes as C
 u=C.windll.user32;u.GetParent.argtypes=[C.c_void_p];u.GetParent.restype=C.c_void_p;u.GetWindow.argtypes=[C.c_void_p,C.c_uint];u.GetWindow.restype=C.c_void_p
 assert u.GetWindow(u.GetParent(dialog.winfo_id()),4)==u.GetParent(r.winfo_id())
 assert str(dialog.transient())==str(r) and dialog.grab_current() is dialog and not dialog.attributes('-topmost')
 def children(w):
  for child in w.winfo_children():yield child;yield from children(child)
 next(w for w in children(dialog) if isinstance(w,ttk.Button) and w.cget('text')=='Вернуться').invoke();assert decisions==['cancel'];a.toggle_fullscreen();pump(r);assert not str(top.transient())
 running[0]=False;worst=max(samples);assert worst<.35,worst
 v.renderer.close();top.destroy();a.close()
 print(f'PASS isolated async PDF, stale zoom rejection, warm cache, middle-button scroll/cancel, usable fullscreen modal; max UI heartbeat gap {worst*1000:.0f} ms',flush=True)
