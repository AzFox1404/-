import tempfile,time,tkinter as tk,ctypes as C
from pathlib import Path
from pypdf import PdfWriter
import studio,scanner_ui
from package_build import PackageDialog

def pump(r,seconds=.2):
 end=time.monotonic()+seconds
 while time.monotonic()<end:r.update();time.sleep(.01)
with tempfile.TemporaryDirectory() as td:
 p=Path(td);studio.STORE=p/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны'
 root=tk.Tk();app=studio.Studio(root);errors=[];root.report_callback_exception=lambda *e:errors.append(str(e[1]))
 project=p/'test';(project/'Документы').mkdir(parents=True);(project/'project.json').write_text('{}');pdf=project/'Документы/Паспорт.pdf';w=PdfWriter();w.add_blank_page(400,600)
 with pdf.open('wb') as f:w.write(f)
 app.project=project;dlg=PackageDialog(app)
 scanner_ui.inspect=lambda *a:[dict(path=str(pdf),source=pdf.name,start=1,end=1,type='Паспорт качества',number='1',date='',material='',pages=[''])]
 scanner_ui.scanner(app,files=[pdf]);pump(root,.6)
 u=C.windll.user32;u.GetParent.argtypes=[C.c_void_p];u.GetParent.restype=C.c_void_p;u.GetWindowLongPtrW.argtypes=[C.c_void_p,C.c_int];u.GetWindowLongPtrW.restype=C.c_ssize_t
 for win in (dlg.window,app.active_scan):
  assert len(win.utility_ribbon.winfo_children())==3
  style=u.GetWindowLongPtrW(u.GetParent(win.winfo_id()),-16);assert not style & (0x10000|0x20000) and style & 0x80000
  win.utility_actions['hide']();pump(root);assert win.state()=='withdrawn' and root.state()!='iconic';assert win.restore_link.winfo_viewable()
  win.restore_link.invoke();pump(root);assert win.state()=='normal'
  app.maximize(win);pump(root);assert win.state()=='zoomed';app.maximize(win);pump(root);assert win.state()=='normal'
  win.utility_actions['separate']();pump(root);assert not str(win.transient()) and win.utility_detached
  win.utility_actions['separate']();pump(root);assert str(win.transient())==str(root) and not win.utility_detached
  assert all(c.has_hint for c in win.utility_ribbon.winfo_children())
 dlg.close_dialog();app.active_scan.tk.call(app.active_scan.protocol('WM_DELETE_WINDOW'));pump(root);app.project=None
 assert not errors,errors
 app.close();print('PASS scanner/PDF utility ribbons, close-only native captions, local hide + return, maximize/restore, detach/attach, hints, cleanup')
