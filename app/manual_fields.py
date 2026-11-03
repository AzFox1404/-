"""Explicit supplemental mappings. Existing detected ranges always take priority."""
from pathlib import Path
import json,hashlib,re
from docx import Document
from word_fields import text,caption
from app_paths import DATA_DIR
FILE=DATA_DIR/'Библиотека'/'Ручные привязки.json'
def rules():
 try:return json.loads(FILE.read_text('utf-8'))
 except (OSError,ValueError):return {}
def signature(doc):
 ps=doc._element.body.xpath('.//w:p');labels=[(i,text(p).strip()) for i,p in enumerate(ps) if caption(text(p)) or re.match(r'^(АКТ|ИСПОЛНИТЕЛЬНАЯ ДОКУМЕНТАЦИЯ|РЕЕСТР|Представитель|Лицо,)',text(p).strip(),re.I)]
 if not labels:labels=[(i,text(p)) for i,p in enumerate(ps)]
 shape=[len(ps),labels,[len(t.rows) for t in doc.tables],[len(t.columns) for t in doc.tables]]
 return hashlib.sha256(json.dumps(shape,ensure_ascii=False).encode()).hexdigest()
def revision():
 from sample_forms import revision as sample_revision
 return hashlib.sha256((FILE.read_bytes() if FILE.exists() else b'')+sample_revision().encode()).hexdigest()
def apply(doc,add,claimed):
 ps=doc._element.body.xpath('.//w:p');applied=False
 for n,r in enumerate(rules().get(signature(doc),[])):
  i=r['paragraph'];a=r['start'];b=r['end']
  if i>=len(ps) or not 0<=a<=b<=len(text(ps[i])):continue
  if caption(text(ps[i])) or any(j==i and a<y and b>x for j,x,y in claimed):continue
  add('manual'+str(n),r['label'],[(i,a,b)]);applied=True
 return applied

def existing_overlap(paragraph,start,end,spec):
 from docx.oxml.ns import qn
 offset=0;begins={};ends={}
 for node in paragraph.iter():
  parent=node.getparent()
  while parent is not None and parent.tag!=qn('w:p'):parent=parent.getparent()
  if parent is not paragraph:continue
  if node.tag==qn('w:bookmarkStart'):begins[node.get(qn('w:name'))]=(node.get(qn('w:id')),offset)
  elif node.tag==qn('w:bookmarkEnd'):ends[node.get(qn('w:id'))]=offset
  elif node.tag==qn('w:t'):offset+=len(node.text or '')
  elif node.tag in (qn('w:tab'),qn('w:br'),qn('w:cr')) and any(a.tag==qn('w:r') for a in node.iterancestors()):offset+=1
 for entry in spec.values():
  for part in entry.get('segments',[]):
   if part['bookmark'] in begins:
    identifier,a=begins[part['bookmark']];b=ends.get(identifier,a)
    if (start<b and end>a) or start==end==a==b:return True
 return False

def dialog(app):
 session=app.current
 if not session:return
 if session.copy.suffix.lower() in ('.xls','.xlsx'):
  from manual_excel import dialog as excel_dialog
  excel_dialog(app);return
 if session.copy.suffix.lower() not in ('.doc','.docx'):
  from app_dialogs import messagebox
  messagebox.showinfo('Привязки','Для известных Excel-форм сохранены действующие правила. Новый редактор привязок пока работает с Word.');return
 old_values=dict(app.models.get(session,{}))
 def ready():
  from tkinter import ttk
  from app_dialogs import messagebox
  import tkinter as tk
  from word_fields import prepare_word
  plan=prepare_word(session.copy,session.preview_dir/'manual-inspect')
  doc=Document(session.copy if session.copy.suffix.lower()=='.docx' else Path(plan['prepared']).with_name('converted.docx'));ps=doc._element.body.xpath('.//w:p');win=tk.Toplevel(app.root);win.title('Дополнительное поле Word');win.geometry('850x540');win.grab_set()
  ttk.Label(win,text='Автоматические правила сохраняются. Выберите текст значения и выделите точные символы. Пустые места и постоянные подписи не предлагаются.',wraplength=800,padding=10).pack(fill='x')
  candidates=[]
  from sample_forms import suggestions_word
  suggestions=suggestions_word(doc)
  for i,p in enumerate(ps):
   v=text(p).strip()
   if not v:
    previous=text(ps[i-1]).strip() if i else ''
    if p.xpath('.//w:u | ./w:pPr/w:pBdr/w:bottom') and re.match(r'^(Объект|Заказчик|Дата|Номер|Адрес|Материалы|Приложения|Представитель|Дополнительные сведения)',previous,re.I):candidates.append(i)
    continue
   if caption(v) or re.match(r'^(Подпись|Представитель|Лицо,|Объект капитального|Застройщик|АКТ|РЕЕСТР|ИСПОЛНИТЕЛЬНАЯ)',v,re.I):continue
   if any(v==str(f['value']).strip() for f in session.spec.values()):continue
   if re.match(r'^\d+\.\s|^(Приложения|ЗАКАЗЧИК|Объект)\s*:?$',v,re.I):continue
   candidates.append(i)
  lb=tk.Listbox(win,height=8,exportselection=False);lb.pack(fill='both',expand=True,padx=10)
  for i in candidates:lb.insert('end',('Образец: '+suggestions[i]['label']+' · ' if i in suggestions else '')+(text(ps[i])[:180] if text(ps[i]).strip() else 'Пустая подчёркнутая строка после: '+text(ps[i-1])[:100]))
  area=tk.Text(win,height=5,wrap='word');area.pack(fill='x',padx=10)
  def select(e):
   if lb.curselection():
    i=candidates[lb.curselection()[0]];area.delete('1.0','end');area.insert('1.0',text(ps[i]))
    proposal=suggestions.get(i);label.set(proposal['label'] if proposal else '')
  lb.bind('<<ListboxSelect>>',select)
  empty=tk.BooleanVar();ttk.Checkbutton(win,text='Подтверждаю: выбранная пустая подчёркнутая строка предназначена для заполнения',variable=empty).pack(anchor='w',padx=10)
  label=tk.StringVar();ttk.Label(win,text='Название нового поля').pack(anchor='w',padx=10);ttk.Entry(win,textvariable=label).pack(fill='x',padx=10)
  def save():
   if not lb.curselection() or not label.get().strip():return
   i=candidates[lb.curselection()[0]]
   if not text(ps[i]).strip():
    if not empty.get():messagebox.showinfo('Привязка','Подтвердите назначение пустой подчёркнутой строки.');return
    a=b=len(text(ps[i]))
   else:
    try:a=len(area.get('1.0','sel.first'));b=len(area.get('1.0','sel.last'))
    except tk.TclError:messagebox.showinfo('Привязка','Выделите только заменяемое значение.');return
   i=candidates[lb.curselection()[0]]
   if area.get('1.0','end-1c')!=text(ps[i]):messagebox.showerror('Привязка','Текст образца нельзя изменять в этом окне. Выделите диапазон заново.');return
   if existing_overlap(ps[i],a,b,session.spec):messagebox.showerror('Привязка','Это значение уже связано с существующим полем. Действующая привязка сохранена.');return
   if re.match(r'^(Подпись|Представитель|Лицо,|Застройщик|АКТ|РЕЕСТР)',text(ps[i])[a:b].strip(),re.I):messagebox.showerror('Привязка','Выбрана постоянная подпись, а не значение.');return
   if not messagebox.askyesno('Подтверждение привязки',f'Создать поле «{label.get()}» для:\n'+text(ps[i])[a:b]+'\n\nПравило будет применяться только к формам с совпадающей структурой и постоянными подписями.'):return
   data=rules();data.setdefault(signature(doc),[]).append(dict(paragraph=i,start=a,end=b,label=label.get().strip()));FILE.parent.mkdir(parents=True,exist_ok=True);tmp=FILE.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf-8');tmp.replace(FILE)
   # Extend the existing bookmark map; never regenerate or replace its fields.
   import copy,uuid
   from word_fields import bookmark,VERSION
   from project_analysis import digest
   key='manual_'+uuid.uuid4().hex[:10];name='BID_'+key
   ids=[int(n.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id','0')) for n in doc._element.xpath('.//w:bookmarkStart')]
   bookmark(ps[i],a,b,name,max([10000]+ids)+1)
   prepared=app.project/'.analysis'/(key+'.docx');prepared.parent.mkdir(parents=True,exist_ok=True);doc.save(prepared)
   updated=copy.deepcopy(session.analysis);updated.update(kind=session.analysis['kind'] if session.analysis['kind']!='unknown' else 'custom',version=VERSION,prepared=str(prepared.relative_to(app.project)),manualRevision=revision())
   updated['warnings']=[w for w in updated.get('warnings',[]) if 'Тип формы не распознан' not in w]
   updated['fields']=copy.deepcopy(session.spec)
   for k,v in old_values.items():
    if k in updated['fields']:updated['fields'][k]['value']=v
   sample=text(ps[i])[a:b];updated['fields'][key]=dict(dest=name,segments=[dict(bookmark=name,sample=sample,capacity=max(1,b-a))],value=sample,label=label.get().strip(),kind='text',word=True,worddate=False,sample=sample)
   index=app.project/'document-analysis.json'
   content=json.loads(index.read_text('utf-8')) if index.exists() else dict(version=1,complete=False,documents={})
   content['documents'][str(session.copy.relative_to(app.project))]=dict(hash=digest(session.copy),plan=updated)
   temp=index.with_suffix('.tmp');temp.write_text(json.dumps(content,ensure_ascii=False,indent=2),'utf-8');temp.replace(index)
   from sample_forms import remember,word_profile
   remember(word_profile(prepared,updated['fields']))
   win.destroy();app.open(session.source,True)
  ttk.Button(win,text='Проверить и сохранить привязку',command=save).pack(anchor='e',padx=10,pady=10)
  win.protocol('WM_DELETE_WINDOW',lambda:(win.destroy(),app.open(session.source,True)));app.paint(win)
 app.stop_sessions([session],ready,require_saved=True)
