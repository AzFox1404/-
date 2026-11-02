"""Sequential project inspection, cached maps and user review of detected conflicts."""
from pathlib import Path
import hashlib,json,queue,threading,copy
import tkinter as tk
from tkinter import ttk,messagebox

KINDS={'act':'Акт','quality':'Реестр качества','registry':'Реестр','title':'Титул','unknown':'Нужна проверка','custom':'Пользовательская форма'}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def field_map_path(source):
    for parent in source.parents:
        if (parent/'project.json').is_file():
            key=hashlib.sha256(str(source.relative_to(parent)).encode('utf-8')).hexdigest()[:24]
            return parent/'.analysis'/'field-maps'/(key+'.json')
    return source.parent/'.bureau-field-maps'/(hashlib.sha256(source.name.encode('utf-8')).hexdigest()[:24]+'.json')

def saved_word_plan(source):
    from word_fields import VERSION
    preferred=field_map_path(source)
    candidates=[preferred]+[p for p in preferred.parent.glob('*.json') if p!=preferred]
    fingerprint=None
    for candidate in candidates:
        try:
            data=json.loads(candidate.read_text('utf-8'))
            if fingerprint is None:fingerprint=digest(source)
            if data['hash']==fingerprint and data['plan']['version']==VERSION:return {**data['plan'],'prepared':None}
        except (OSError,ValueError,KeyError):pass

def save_word_plan(source,plan,spec,values):
    saved=copy.deepcopy(plan);saved.pop('prepared',None);saved['fields']=copy.deepcopy(spec)
    for key,value in values.items():
        if key in saved['fields']:saved['fields'][key]['value']=value
    saved['warnings']=[w for w in saved.get('warnings',[]) if not ('В АОСР' in w and 'к АООК' not in values.get('attachments',''))]
    target=field_map_path(source);target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_suffix('.tmp');temp.write_text(json.dumps(dict(hash=digest(source),plan=saved),ensure_ascii=False,indent=2),'utf-8');temp.replace(target)

def preferred_word_plan(source):
    saved=saved_word_plan(source);cached=cached_word_plan(source)
    if cached and saved and cached.get('manualRevision')!=saved.get('manualRevision'):return cached
    return saved or cached

def cached_word_plan(source):
    for parent in source.parents:
        index=parent/'document-analysis.json'
        if not index.exists():continue
        try:
            item=json.loads(index.read_text('utf-8'))['documents'].get(str(source.relative_to(parent)))
            from word_fields import VERSION
            if item and item.get('hash')==digest(source) and item['plan'].get('version')==VERSION and item['plan'].get('manualRevision',__import__('manual_fields').revision())==__import__('manual_fields').revision():
                plan=item['plan'];prepared=parent/plan['prepared']
                if prepared.is_file():return {**plan,'prepared':str(prepared)}
        except (ValueError,KeyError,OSError):pass
        break

class ProjectAnalysis:
    def analyze_import(self,project,callback):
        files=[p for p in (project/'Документы').rglob('*') if p.suffix.lower() in ('.doc','.docx','.xls','.xlsx') and not p.name.startswith('~$')]
        events=queue.Queue();cancel=threading.Event()
        win=tk.Toplevel(self.root);win.title('Анализ документов проекта');win.geometry('500x160');win.transient(self.root)
        status=tk.StringVar(value='Определяем типы документов и заполняемые поля…')
        ttk.Label(win,textvariable=status,wraplength=460,padding=18).pack(fill='x')
        bar=ttk.Progressbar(win,maximum=max(1,len(files)));bar.pack(fill='x',padx=18,pady=6)
        ttk.Button(win,text='Остановить анализ',command=cancel.set).pack(anchor='e',padx=18,pady=8)
        win.protocol('WM_DELETE_WINDOW',cancel.set);self.paint(win);win.grab_set()
        def work():
            from office_forms import extra_fields
            from act_layout import act_rows
            from word_fields import prepare_word
            documents={}
            for i,path in enumerate(files):
                if cancel.is_set():break
                events.put(('progress',(i,path.name)))
                try:
                    sha=digest(path)
                    if path.suffix.lower() in ('.doc','.docx'):
                        plan=prepare_word(path,project/'.analysis'/sha[:20]);plan['prepared']=str(Path(plan['prepared']).relative_to(project))
                    elif path.suffix.lower()=='.xlsx':
                        fields=extra_fields(path);layout=act_rows(path)
                        kind='act' if layout else 'quality' if 'actRef' in fields else 'registry' if fields else 'unknown'
                        plan=dict(kind=kind,fields=fields,warnings=[] if fields or layout else ['Шаблон не распознан уверенно. Постоянный текст не назначен полями.'],layout=layout)
                    else:plan=dict(kind='unknown',fields={},warnings=['Для старой формы XLS пока доступны только явно назначенные ID-поля.'])
                    documents[str(path.relative_to(project))]=dict(hash=sha,plan=plan)
                except Exception as exc:documents[str(path.relative_to(project))]=dict(plan=dict(kind='unknown',fields={},warnings=['Не удалось проанализировать: '+str(exc)]))
            output=dict(version=1,complete=not cancel.is_set(),documents=documents)
            target=project/'document-analysis.json';temp=target.with_suffix('.tmp');temp.write_text(json.dumps(output,ensure_ascii=False,indent=2),'utf-8');temp.replace(target)
            events.put(('done',output))
        def safe_work():
            try:work()
            except Exception as exc:events.put(('error',str(exc)))
        threading.Thread(target=safe_work,daemon=True).start()
        def poll():
            if not win.winfo_exists():return
            while not events.empty():
                kind,data=events.get()
                if kind=='progress':i,name=data;status.set(f'Документ {i+1} из {len(files)}\n{name}');bar['value']=i
                elif kind=='error':
                    win.grab_release();win.destroy();messagebox.showerror('Анализ документов',data);callback();return
                else:
                    win.grab_release();win.destroy();callback()
                    self.root.after(200,lambda:self.analysis_report(project,data));return
            self.root.after(100,poll)
        poll()

    def analysis_report(self,project,data=None):
        if data is None:
            try:data=json.loads((project/'document-analysis.json').read_text('utf-8'))
            except (OSError,ValueError):self.analyze_import(project,lambda:None);return
        win=tk.Toplevel(self.root);win.title('Результат анализа документов');win.geometry('900x460');win.minsize(650,300)
        ttk.Label(win,text=('Поля определены по структуре документов. Исходные обозначения и состав колонок сохранены.' if data.get('complete') else 'Анализ остановлен: проверены не все документы. Исходные обозначения сохранены.'),wraplength=850,padding=12).pack(fill='x')
        nav=ttk.Frame(win);nav.pack(fill='x',padx=12)
        frame=ttk.Frame(win);frame.pack(fill='both',expand=True,padx=12)
        tree=ttk.Treeview(frame,columns=('kind','fields','check'),show='tree headings');tree.heading('#0',text='Документ');tree.column('#0',width=440)
        for key,label,width in [('kind','Тип',130),('fields','Полей',60),('check','Проверка',130)]:tree.heading(key,text=label);tree.column(key,width=width)
        y=ttk.Scrollbar(frame,command=tree.yview);tree.configure(yscrollcommand=y.set);y.pack(side='right',fill='y');tree.pack(fill='both',expand=True)
        notes=tk.StringVar(value='Выберите документ для просмотра замечаний.')
        ttk.Label(win,textvariable=notes,wraplength=850,padding=12).pack(fill='x')
        checked=set(data['documents'])
        def move(step):
            rows=list(tree.get_children());current=tree.focus();index=rows.index(current)+step if current in rows else 0
            if rows:
                node=rows[max(0,min(len(rows)-1,index))];tree.selection_set(node);tree.focus(node);tree.see(node)
        def marks(enabled):
            checked.clear()
            if enabled:checked.update(data['documents'])
            for node in tree.get_children():tree.item(node,text=('☑ ' if node in checked else '☐ ')+node)
        def toggle(e):
            node=tree.identify_row(e.y)
            if node and e.x<28:
                checked.discard(node) if node in checked else checked.add(node)
                tree.item(node,text=('☑ ' if node in checked else '☐ ')+node);return 'break'
        for key,label,fn in [('up','Предыдущий файл',lambda:move(-1)),('down','Следующий файл',lambda:move(1)),('checkall','Отметить все',lambda:marks(True)),('uncheckall','Снять отметки',lambda:marks(False))]:self.icon_button(nav,key,label,fn)
        tree.bind('<Up>',lambda e:(move(-1),'break')[1]);tree.bind('<Down>',lambda e:(move(1),'break')[1]);tree.bind('<Button-1>',toggle,add='+')
        items=data['documents']
        for name,item in items.items():
            plan=item['plan'];tree.insert('','end',iid=name,text='☑ '+name,values=(KINDS[plan['kind']],len(plan['fields']) or len((plan.get('layout') or {}).get('fields',{})),'Нужна проверка' if plan['warnings'] else 'Распознано'))
        def select(e=None):
            names=tree.selection()
            if names:notes.set('\n'.join(items[names[0]]['plan']['warnings']) or 'Неоднозначных обозначений не обнаружено. Проверьте заполнение по предпросмотру.')
        def open_doc():
            names=tree.selection()
            if names and names[0] in checked and self.project==project:self.open(project/names[0]);win.destroy()
        tree.bind('<<TreeviewSelect>>',select);tree.bind('<Double-1>',lambda e:open_doc())
        ttk.Button(win,text='Открыть выбранный документ',command=open_doc).pack(anchor='e',padx=12,pady=10);self.paint(win)

    def review_word_fields(self):
        session=self.current;plan=getattr(session,'analysis',{})
        if not plan:return
        if not session.spec:
            messagebox.showinfo('Проверка полей','\n'.join(plan['warnings']) or 'В этой форме пока не удалось уверенно определить поля.');return
        win=tk.Toplevel(self.root);win.title('Проверка распознанных полей');win.geometry('720x420')
        ttk.Label(win,text='\n'.join(plan['warnings']) or 'Проверьте значения распознанных полей перед заполнением.',wraplength=680,padding=12).pack(fill='x')
        keys=list(session.spec);names={session.spec[k]['label']+' ['+k+']':k for k in keys}
        choice=ttk.Combobox(win,values=list(names),state='readonly');choice.pack(fill='x',padx=12)
        old=tk.StringVar();new=tk.StringVar()
        ttk.Label(win,text='Текущее значение',padding=8).pack(anchor='w');ttk.Label(win,textvariable=old,wraplength=680).pack(fill='x',padx=12)
        ttk.Label(win,text='Предлагаемое значение — можно изменить',padding=8).pack(anchor='w');entry=ttk.Entry(win,textvariable=new);entry.pack(fill='x',padx=12)
        def load(e=None):
            key=names.get(choice.get())
            if not key:return
            value=self.models[session].get(key,'');old.set(value)
            proposal=value.replace('к АООК','к АОСР') if key=='attachments' and any('В АОСР' in warning for warning in plan['warnings']) else value
            new.set(proposal)
        def apply():
            key=names.get(choice.get())
            if not key:return
            if key in self.views:self.views[key].set(new.get())
            else:self.changed(session,key,new.get());self.build(1)
            old.set(new.get())
        choice.bind('<<ComboboxSelected>>',load)
        ttk.Button(win,text='Применить к выбранному полю',command=apply).pack(anchor='e',padx=12,pady=14)
        if names:choice.set(next((name for name,key in names.items() if key=='attachments' and plan['warnings']),next(iter(names))));load()
        self.paint(win)
