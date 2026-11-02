from test_pdf_wait import wait_pdf
import tempfile,time,tkinter as tk,ctypes as C
from pathlib import Path
from types import SimpleNamespace
from tkinter import ttk
import studio
from pdf_page_preview import PagePreview
from package_build import PackageDialog
from windows_integration import monitor_bounds
from pypdf import PdfWriter

def pump(root,n=.3):
 end=time.monotonic()+n
 while time.monotonic()<end:root.update();time.sleep(.01)
with tempfile.TemporaryDirectory() as td:
 studio.STORE=Path(td)/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны'
 root=tk.Tk();app=studio.Studio(root);errors=[];root.report_callback_exception=lambda *e:errors.append(str(e[1]));pump(root)
 bounds=monitor_bounds(root);app.toggle_fullscreen();pump(root,.5)
 assert (root.winfo_rootx(),root.winfo_rooty(),root.winfo_width(),root.winfo_height())==bounds,((root.winfo_rootx(),root.winfo_rooty(),root.winfo_width(),root.winfo_height()),bounds)
 app.toggle_fullscreen();pump(root)
 top=tk.Toplevel(root);top.geometry('650x500');top.title('Проверка схемы');v=PagePreview(top,app,wheel_zoom=True);v.pack(fill='both',expand=True)
 file=Path(td)/'scheme.pdf';w=PdfWriter();w.add_blank_page(1600,1200);w.add_blank_page(1600,1200)
 with file.open('wb') as f:w.write(f)
 v.show(file,0);wait_pdf(root,v);pump(root);v.canvas.xview_moveto(.15);v.canvas.yview_moveto(.1);pump(root)
 x,y=230,170;cx=v.canvas.canvasx(x);cy=v.canvas.canvasy(y);n=v.page_at(cy);old=v.pages[n];fx=(cx-8)/old[1];fy=(cy-old[0])/old[2]
 v.zoom_at(SimpleNamespace(delta=120,x=x,y=y));pump(root);new=v.pages[n]
 assert abs((v.canvas.canvasx(x)-8)/new[1]-fx)<.003
 assert abs((v.canvas.canvasy(y)-new[0])/new[2]-fy)<.02
 v.rotate(90);pump(root);assert v.rotations
 for dark in (False,True):
  app.toggle_theme(int(dark));pump(root)
  holder=ttk.Frame(top);holder.pack();button=app.icon_button(holder,'save','Сохранить документы',lambda:None);button.pack();pump(root);button.event_generate('<Enter>');pump(root,.6)
  tip=button.hint_state['window'];assert tip is not None
  canvas=tip.winfo_children()[0];assert canvas.cget('bg')==('#d3d1d0' if dark else '#ffffff')
  tip.destroy();button.hint_state['window']=None;button.destroy()
 # Navigation visits every leaf, including different groups and collapsed acts.
 tree=ttk.Treeview(top);g=tree.insert('','end');a=tree.insert(g,'end',iid='f0');b=tree.insert(a,'end',iid='f1');g2=tree.insert('','end');tree.insert(g2,'end',iid='f2')
 dialog=SimpleNamespace(tree=tree);tree.focus('f0');PackageDialog.move(dialog,1);assert tree.focus()=='f1';PackageDialog.move(dialog,1);assert tree.focus()=='f2';PackageDialog.move(dialog,-1);assert tree.focus()=='f1'
 # Assembly controls are compact and linking is aligned to the right.
 from openpyxl import Workbook
 project=Path(td)/'project';(project/'Документы').mkdir(parents=True);(project/'project.json').write_text('{}')
 Workbook().save(project/'Документы/АОСР 1.xlsx')
 import shutil
 shutil.copyfile(file,project/'Документы/Паспорт.pdf');app.project=project
 dlg=PackageDialog(app);pump(root)
 assert dlg.go.winfo_reqheight()<35 and dlg.go.cget('image') and dlg.go.has_hint
 i=next(i for i,it in enumerate(dlg.items) if it.role=='Паспорт');dlg.tree.focus('f'+str(i));dlg.link();pump(root)
 link=next(w for w in dlg.window.winfo_children() if isinstance(w,tk.Toplevel))
 def descendants(w):
  for c in w.winfo_children():yield c;yield from descendants(c)
 apply=next(w for w in descendants(link) if isinstance(w,ttk.Button) and w.cget('text')=='Применить')
 assert apply.pack_info()['side']=='right' and apply.cget('image')
 assert app.style.lookup('Package.Treeview.Heading','foreground',('active',))=='#111111'
 link.destroy();dlg.close_dialog();app.project=None
 assert not errors,errors
 top.destroy();app.close()
 print('PASS fullscreen bounds, cursor anchored zoom, rotation, white/gray readable hints, all-file navigation',flush=True)
