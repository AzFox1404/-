"""Conservative checks before a print package is built."""
from datetime import datetime
import re

def issues(app,items):
 out=[];numbers={}
 for item in items:
  if not item.path.exists():out.append((item.path,'Отсутствует файл'));continue
  if item.role=='Акт':
   key=(item.section,item.number)
   if item.number and key in numbers:out.append((item.path,'Повтор номера акта: '+item.number))
   numbers[key]=item.path
  if item.role=='Приложение' and not item.parent:out.append((item.path,'Не указана связь приложения с актом'))
  s=app.sessions.get(item.path)
  if not s:
   from types import SimpleNamespace
   from project_analysis import saved_word_plan,cached_word_plan
   plan=(saved_word_plan(item.path) or cached_word_plan(item.path)) if item.path.suffix.lower() in ('.doc','.docx') else None
   if not plan and item.path.suffix.lower()=='.docx':
    from word_fields import analyze_word
    plan=analyze_word(item.path)
   if not plan and item.path.suffix.lower()=='.xlsx':
    from act_layout import act_rows
    from office_forms import extra_fields
    from openpyxl import load_workbook
    from package_build import date_str
    layout=act_rows(item.path);spec=extra_fields(item.path);vals={k:v['value'] for k,v in spec.items()}
    if layout:
     w=load_workbook(item.path,data_only=True);sheet=w.active
     for k,coords in layout['fields'].items():vals[k]=' '.join(str(sheet[c].value or '') for c in coords)
     for k in ('start','end','date'):vals[k]=date_str(vals.get(k,''))
     w.close()
    plan=dict(fields={k:dict(value=v) for k,v in vals.items()},warnings=[])
   if not plan:
    if item.path.suffix.lower() in ('.doc','.docx','.xls','.xlsx'):out.append((item.path,'Поля формы не распознаны: требуется ручная проверка'))
    continue
   if not plan['fields'] and item.role in ('Акт','Документ'):out.append((item.path,'Поля формы не распознаны: требуется ручная проверка'))
   s=SimpleNamespace(analysis=plan);vals={k:v['value'] for k,v in plan['fields'].items()}
  else:vals=app.models.get(s,{})
  if item.role=='Акт':
   for key,label in [('address','Объект'),('number','Номер'),('work','Работы'),('workStart','Начало работ'),('workEnd','Окончание работ'),('actDate','Дата акта'),('start','Начало работ'),('end','Окончание работ')]:
    if key in vals and not str(vals[key]).strip():out.append((item.path,'Не заполнено: '+label))
   start=vals.get('workStart',vals.get('start'));end=vals.get('workEnd',vals.get('end'))
   def date(v):
    for fmt in ('%Y-%m-%d','%d.%m.%Y'):
     try:return datetime.strptime(v,fmt)
     except (ValueError,TypeError):pass
   if date(start) and date(end) and date(start)>date(end):out.append((item.path,'Начало работ позже окончания'))
  if item.role=='Акт' and re.search(r'приложени[ея]\s*№',vals.get('materials',''),re.I) and not any(x.role=='Приложение' and x.parent==item.path for x in items):out.append((item.path,'Не выбрано приложение, указанное в акте'))
  catalogue=app.quality_records() if hasattr(app,'quality_records') else []
  reference=vals.get('materials','')+' '+vals.get('attachments','')
  row_numbers={str(v).replace('№','').strip() for k,v in vals.items() if re.match(r'row\d+_4$',k)}
  for record in catalogue:
   number=str(record.get('number','')).replace('№','').strip()
   if number and (number in row_numbers or re.search(r'(?:паспорт|сертификат|декларация).{0,80}№\s*'+re.escape(number)+r'(?![\w\d])',reference,re.I)) and not any(x.role=='Паспорт' and (str(x.path)==record['file'] or str(x.number).replace('№','').strip()==number) for x in items):out.append((item.path,'Не выбран документ качества №'+number))
  for warning in getattr(s,'analysis',{}).get('warnings',[]):
   if 'В АОСР' in warning and 'к АООК' not in vals.get('attachments',''):continue
   out.append((item.path,warning))
 return out

def show(app,items):
 import tkinter as tk
 from tkinter import ttk
 found=issues(app,items)
 if not found:return False
 signature=tuple((str(p),m) for p,m in found)
 if getattr(app,'package_check_ack',None)==signature:return False
 win=tk.Toplevel(app.root);win.title('Проверка комплекта');win.geometry('850x400')
 ttk.Label(win,text='Найдены замечания. Двойной щелчок открывает документ. Исправьте данные и повторите сборку.',wraplength=800,padding=12).pack(fill='x')
 tree=ttk.Treeview(win,columns=('message',),show='tree headings');tree.heading('#0',text='Документ');tree.heading('message',text='Замечание');tree.column('message',width=480);tree.pack(fill='both',expand=True)
 for i,(path,message) in enumerate(found):tree.insert('','end',iid=str(i),text=path.name,values=(message,))
 tree.bind('<Double-1>',lambda e:app.open(found[int(tree.selection()[0])][0]) if tree.selection() else None)
 if not any(m.startswith('Отсутствует') for p,m in found):
  def acknowledge():app.package_check_ack=signature;win.destroy()
  ttk.Button(win,text='Замечания проверены — разрешить повторную сборку',command=acknowledge).pack(anchor='e',padx=10,pady=8)
 app.paint(win);return True
