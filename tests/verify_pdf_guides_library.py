"""Generated Office geometry, retained PDF frame, compact library actions."""
import tempfile,queue,time,tkinter as tk
from pathlib import Path
from openpyxl import Workbook
import pymupdf as fitz
import studio
from workspace_preview import Session
from pdf_page_preview import PagePreview

def wait(root,fn):
 end=time.monotonic()+60
 while time.monotonic()<end:
  root.update();time.sleep(.01)
  if fn():return
 raise AssertionError('timeout')

with tempfile.TemporaryDirectory() as td:
 p=Path(td);file=p/'Registry.xlsx';w=Workbook();ws=w.active
 ws['B8']='Наименование документа';ws['C8']='Номер документа'
 for row in (9,10,11):ws.cell(row,1,row-8);ws.cell(row,2,'ROW'+str(row));ws.cell(row,5,1)
 ws['B12']='Всего страниц:';ws.print_area='A1:E12';w.save(file);w.close()
 s=Session(file,queue.Queue(),prepared=True)
 try:
  while True:
   _,kind,data=s.events.get(timeout=90)
   if kind=='error':raise AssertionError(data)
   if kind=='pdf':pdf=data[1];break
  assert s.guides['kind']=='excel' and not s.guides.get('unsupported'),s.guides
  assert any(r['name']=='9' for r in s.guides['rows'])
  studio.STORE=p/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны'
  root=tk.Tk();app=studio.Studio(root);errors=[];root.report_callback_exception=lambda *e:errors.append(str(e[1]))
  top=tk.Toplevel(root);view=PagePreview(top,app);view.pack(fill='both',expand=True);view.guides=s.guides;view.show(pdf,0)
  wait(root,lambda:bool(view.images));view.rulers.draw();assert view.rulers.hits
  doc=fitz.open(stream=pdf,filetype='pdf');word=next(word for word in doc[0].get_text('words') if word[4]=='ROW9')
  _,_,row=next(hit for hit in view.rulers.hits if hit[2]==9)
  hit=next(hit for hit in view.rulers.hits if hit[2]==row)
  center=view.pages[0][0]+(word[1]+word[3])/2*view.zoom/75-view.canvas.canvasy(0)
  assert hit[0]-4<=center<=hit[1]+4,(hit,center)
  doc[0].insert_text((30,200),'UPDATED');new=doc.tobytes();doc.close()
  old=view.canvas.find_all();view.show(new,0,retain=True)
  assert view.canvas.find_all()==old and view.images,'old frame was cleared before replacement'
  wait(root,lambda:view._sizes is not None and bool(view.images))
  app.library_tree(top);root.update()
  buttons=[c for frame in top.winfo_children() if getattr(frame,'panel_toolbar',False) for c in frame.winfo_children()]
  assert len(buttons)==2 and buttons[0].winfo_y()==buttons[1].winfo_y()
  project=p/'project';(project/'Документы').mkdir(parents=True);(project/'project.json').write_text('{}')
  app.enter(project);root.update();app.detach(3);root.update();app.windows[3].geometry('180x240');app.enforce_panel_sizes();root.update()
  host=app.windows[3]
  for bar in host.winfo_children():
   if not getattr(bar,'panel_toolbar',False):continue
   for button in bar.winfo_children():assert button.winfo_x()+button.winfo_width()<=bar.winfo_width()
  source=studio.LIB/'Титулы'/'Test.docx';source.write_bytes(b'template');app.selected[3]=str(source)
  app.folder_name=lambda initial:'Renamed.docx';app.build=lambda n:None
  app.library_change(False);renamed=source.with_name('Renamed.docx');assert renamed.read_bytes()==b'template'
  original=studio.messagebox.askyesno;studio.messagebox.askyesno=lambda *a,**k:True
  try:app.library_change(True);assert not renamed.exists()
  finally:studio.messagebox.askyesno=original
  app.journal().temp.cleanup();top.destroy();root.destroy();assert not errors,errors
  print('PASS Office row geometry matches PDF text; frame retained; same-line library actions; rename/delete')
 finally:s.tasks.put(None);s.thread.join(30)
