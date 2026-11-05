"""Explicit additional bindings for unknown XLSX forms; no blank-cell suggestions."""
import hashlib,json,re
from pathlib import Path
from openpyxl import load_workbook
from tkinter import ttk
from app_dialogs import messagebox
import tkinter as tk
import manual_fields
from office_forms import instruction

def signature(sheet):
 anchors=[(c.coordinate,str(c.value)) for row in sheet for c in row if c.value and (instruction(c.value) or re.search(r'номер|дата|объект|подпись|наименование',str(c.value),re.I))]
 if not anchors:anchors=[(c.coordinate,str(c.value)) for row in sheet for c in row if c.value is not None]
 return 'excel:'+hashlib.sha256(json.dumps([sheet.max_row,sheet.max_column,sorted(str(m) for m in sheet.merged_cells.ranges),anchors],ensure_ascii=False).encode()).hexdigest()
def fields(path,existing):
 if path.suffix.lower()!='.xlsx':return existing
 w=load_workbook(path);s=w.worksheets[0]
 try:
  for name in w.defined_names:
   if name.startswith('ID_User_'):
    destinations=list(w.defined_names[name].destinations)
    if destinations and destinations[0][0]==s.title:
     cell=s[destinations[0][1].replace('$','')];existing[name]=dict(dest=cell.coordinate,value=str(cell.value or ''),label=manual_fields.rules().get('_names',{}).get(name,name),kind='text',prefix='')
  for i,rule in enumerate(manual_fields.rules().get(signature(s),[])):
   c=s[rule['cell']]
   if c.__class__.__name__=='MergedCell' or c.data_type=='f' or instruction(c.value) or c.coordinate in {v['dest'] for v in existing.values()}:continue
   existing['manualXL'+str(i)]=dict(dest=c.coordinate,value=str(c.value or ''),label=rule['label'],kind='text',prefix='')
  from sample_forms import apply_excel
  return apply_excel(s,existing)
 finally:w.close()
def dialog(app):
 session=app.current
 if not session or session.copy.suffix.lower() not in ('.xls','.xlsx'):return
 from act_layout import act_rows
 if (session.spec and not all(k.startswith(('manualXL','ID_User_')) for k in session.spec)) or act_rows(session.copy):messagebox.showinfo('Привязки','Существующие поля сохранены. Редактор предназначен для неизвестных форм XLSX.');return
 win=tk.Toplevel(app.root);win.title('Поле неизвестной формы Excel');win.geometry('620x380');win.grab_set()
 inspection=session.copy
 if inspection.suffix.lower()=='.xls':
  import subprocess,tempfile
  inspection=Path(tempfile.gettempdir())/('bureau-inspect-'+__import__('uuid').uuid4().hex+'.xlsx')
  try:subprocess.run(['powershell.exe','-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',str(Path(__file__).with_name('InspectExcel.ps1')),'-Source',str(session.copy),'-Target',str(inspection)],check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=60)
  except Exception as exc:win.destroy();messagebox.showerror('Анализ XLS',str(exc));return
 w=load_workbook(inspection);s=w.worksheets[0];choices=[]
 from sample_forms import suggestions_excel
 suggestions=suggestions_excel(s)
 for row in s:
  for c in row:
   if c.value is None:
    near=[s.cell(c.row,c.column-1).value if c.column>1 else None,s.cell(c.row-1,c.column).value if c.row>1 else None]
    if c.__class__.__name__!='MergedCell' and (c.border.bottom.style or c.font.underline) and any(v and re.match(r'^(Объект|Заказчик|Дата|Номер|Адрес|Материал|Представитель)',str(v),re.I) for v in near):choices.append(c.coordinate+' — Пустая подчёркнутая ячейка рядом с подписью')
    continue
   if c.coordinate in {v['dest'] for v in session.spec.values()} or c.data_type=='f' or instruction(c.value) or re.match(r'^(Подпись|Представитель|АКТ|РЕЕСТР)',str(c.value),re.I):continue
   choices.append(c.coordinate+' — '+str(c.value)[:100])
 ttk.Label(win,text='Выберите ячейку со значением. Сравнение с заполненной формой подсказывает пустые области для проверки.',wraplength=580,padding=12).pack(fill='x')
 lb=tk.Listbox(win,exportselection=False);lb.pack(fill='both',expand=True,padx=12)
 for choice in choices:
  cell=choice.split(' — ')[0];lb.insert('end',choice+(' · Образец: '+suggestions[cell] if cell in suggestions else ''))
 label=tk.StringVar();ttk.Entry(win,textvariable=label).pack(fill='x',padx=12,pady=6)
 def propose(e):
  if lb.curselection():label.set(suggestions.get(choices[lb.curselection()[0]].split(' — ')[0],''))
 def compare():
  from tkinter import filedialog
  from form_comparison import excel_candidates
  path=filedialog.askopenfilename(parent=win,title='Заполненный экземпляр формы',filetypes=[('Excel','*.xlsx')])
  if not path:return
  try:
   sample=load_workbook(path)
   try:found=excel_candidates(s,sample.worksheets[0])
   finally:sample.close()
  except Exception as exc:messagebox.showerror('Сравнение форм',str(exc));return
  known={choice.split(' — ')[0] for choice in choices}|{v['dest'] for v in session.spec.values()}
  for cell in sorted(found-known,key=lambda name:(s[name].row,s[name].column)):
   choices.append(cell+' — Пустая область найдена сравнением');lb.insert('end',choices[-1])
  if not found-known:messagebox.showinfo('Сравнение форм','Дополнительные области ввода не найдены.')
 ttk.Button(win,text='Сравнить с заполненным XLSX',command=compare).pack(anchor='w',padx=12)
 lb.bind('<<ListboxSelect>>',propose)
 def save():
  if not lb.curselection() or not label.get().strip():return
  cell=choices[lb.curselection()[0]].split(' — ')[0]
  if not messagebox.askyesno('Подтвердить поле',f'Создать поле «{label.get()}» в ячейке {cell}?'):return
  import uuid
  field='ID_User_'+uuid.uuid4().hex[:12]
  data=manual_fields.rules();data.setdefault('_names',{})[field]=label.get().strip();data.setdefault(signature(s),[]).append(dict(cell=cell,label=label.get().strip()));manual_fields.FILE.parent.mkdir(parents=True,exist_ok=True);temp=manual_fields.FILE.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False),'utf-8');temp.replace(manual_fields.FILE)
  from sample_forms import remember,excel_profile
  remember(excel_profile(s,{field:dict(dest=cell,label=label.get().strip(),kind='text')}))
  win.destroy();w.close()
  def bind():
   import subprocess
   try:
    subprocess.run(['powershell.exe','-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',str(Path(__file__).with_name('BindExcel.ps1')),'-Source',str(session.copy),'-Cell',cell,'-Field',field],check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=60)
   except Exception as exc:messagebox.showerror('Привязка',str(exc))
   app.open(session.source,True)
  app.stop_sessions([session],bind,require_saved=True)
 ttk.Button(win,text='Подтвердить привязку',command=save).pack(anchor='e',padx=12,pady=8)
 win.protocol('WM_DELETE_WINDOW',lambda:(w.close(),win.destroy()));app.paint(win)
