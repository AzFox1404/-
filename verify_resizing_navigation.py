import ctypes as C,time,tempfile,tkinter as tk
from ctypes import wintypes as W
from pathlib import Path
from tkinter import ttk
from types import SimpleNamespace
import studio,resize_preview
from package_build import PackageDialog
from pdf_page_preview import PagePreview
from pypdf import PdfWriter
import pypdfium2 as pdfium

def pump(root,seconds=.25):
 end=time.monotonic()+seconds
 while time.monotonic()<end:root.update();time.sleep(.01)
def descendants(w):
 for c in w.winfo_children():yield c;yield from descendants(c)
with tempfile.TemporaryDirectory() as td:
 p=Path(td);studio.STORE=p/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны'
 root=tk.Tk();app=studio.Studio(root);errors=[];root.report_callback_exception=lambda *e:errors.append(str(e[1]));pump(root)
 win=tk.Toplevel(root);win.geometry('660x540');v=PagePreview(win,app);v.pack(fill='both',expand=True);pump(root)
 u=C.windll.user32;u.GetParent.argtypes=[W.HWND];u.GetParent.restype=W.HWND
 hwnd=u.GetParent(win.winfo_id())
 u.GetWindowLongPtrW.argtypes=[W.HWND,C.c_int];u.GetWindowLongPtrW.restype=C.c_ssize_t
 procedure=u.GetWindowLongPtrW(hwnd,-4);resize_preview.install(win)
 assert u.GetWindowLongPtrW(hwnd,-4)==procedure
 for width in (800,690,920,660):win.geometry(f'{width}x540');pump(root,.08)
 file=p/'test.pdf';w=PdfWriter();w.add_blank_page(500,700)
 with file.open('wb') as f:w.write(f)
 from test_pdf_wait import wait_pdf
 v.show(file,0);wait_pdf(root,v);v.set_zoom(100);wait_pdf(root,v);count=v.renderer.render_count;v.set_zoom(70);wait_pdf(root,v)
 assert v.renderer.render_count==count
 project=p/'project';(project/'Документы').mkdir(parents=True);(project/'project.json').write_text('{}')
 for n in range(3):(project/'Документы'/f'Паспорт {n}.pdf').write_bytes(file.read_bytes())
 app.project=project;dlg=PackageDialog(app);pump(root)
 dlg.tree.focus('f0');dlg.tree.focus_force();pump(root);dlg.tree.event_generate('<Down>');pump(root);assert dlg.tree.focus()=='f1'
 option=next(c for c in descendants(dlg.window) if isinstance(c,ttk.Checkbutton));option.focus_force();pump(root);option.event_generate('<Down>');pump(root);assert dlg.tree.focus()=='f2'
 dlg.close_dialog();app.ask_save('Проверка сохранения',lambda result:None);pump(root)
 buttons=[c for c in descendants(app.decision) if isinstance(c,ttk.Button)]
 assert all(b.winfo_reqheight()<35 for b in buttons)
 rightmost=buttons[-1];assert app.decision.winfo_width()-(rightmost.winfo_rootx()-app.decision.winfo_rootx()+rightmost.winfo_width())<22
 # Rounded image corners remain the parent colour without native HWND clipping.
 for dark in (False,True):
  app.toggle_theme(int(dark));pump(root)
  for name in ('Compact','Primary','Window'):
   pictures=app.theme_images[('Dark' if dark else 'Light')+name+'.surface']
   expected=app.colors['accent'] if name=='Window' else app.colors['bg']
   expected=tuple(int(expected[n:n+2],16) for n in (1,3,5))
   for picture in pictures:
    actual=tuple(root.tk.call(str(picture),'get',0,0));assert all(abs(a-b)<=4 for a,b in zip(actual,expected)),(name,actual,expected)
 app.decision.event_generate('<<Unused>>');app.decision.destroy();app.decision=None;win.destroy();app.project=None
 assert not errors,errors
 app.close()
 print('PASS standard native sizing without snapshot hook, cached PDF zoom, arrows from tree and checkbox focus, right-aligned compact save buttons, rounded opaque image corners')

