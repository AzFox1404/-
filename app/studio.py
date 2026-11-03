from pathlib import Path
import json
import os
import shutil
import uuid
import zipfile
import tkinter as tk
from tkinter import ttk, filedialog
from app_dialogs import messagebox, simpledialog
from workspace_preview import Workspace, Session, ROOT, BG, PAPER, ACCENT, NAMES, LABELS, DATES, SAMPLES

OFFICE={'.doc','.docx','.xls','.xlsx'}
from app_paths import DATA_DIR
STORE=DATA_DIR
PROJECTS=STORE/'Проекты'
LIB=STORE/'Библиотека'/'Шаблоны'
NAMES[:]=['Документы','Заполнение','Предпросмотр PDF','Библиотека']
LABELS.update(address='Объект и адрес',client='Застройщик · реквизиты',clientAddress='Адрес застройщика',
 builder='Подрядчик · реквизиты',builderAddress='Адрес подрядчика',number='Номер акта',
 developer='Представитель застройщика · ФИО',builderRep='Представитель подрядчика · ФИО и приказ',
 executorRep='Представитель исполнителя · ФИО и приказ',executorInfo='Реквизиты исполнителя',
 otherRep='Иные представители',executor='Исполнитель работ',project='Проектная документация',
 materials='Материалы и документы качества',hiddenWorks='Освидетельствованные скрытые работы',
 schemes='Исполнительные схемы',reports='Результаты обследований',tests='Испытания',
 standards='Нормативные документы',nextWork='Последующие работы',notes='Дополнительные сведения',
 attachments='Приложения',clientSign='Представитель застройщика · ФИО',
 foreman='Представитель лица, осуществляющего строительство · ФИО',executorSign='Представитель лица, выполнившего работы · ФИО')

def docs(folder):
    return sorted(p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in OFFICE and not p.name.startswith('~$'))

def next_path(path):
    dest=path
    for n in range(2,10000):
        if not dest.exists():return dest
        dest=path.with_name(f'{path.stem} ({n}){path.suffix}')
    raise ValueError('Название занято.')

def write_json(path,data):
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf-8')
    tmp.replace(path)

def unpack(archive,folder):
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            name=member.filename.replace('\\','/')
            dest=(folder/name).resolve()
            if (not dest.is_relative_to(folder.resolve()) or ':' in name or
                any(s.rstrip(' .')!=s or s.split('.')[0].upper() in {'CON','NUL','AUX','PRN',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))} for s in name.split('/') if s)):
                raise ValueError('Недопустимое имя в ZIP: '+name)
            if not member.is_dir():
                dest.parent.mkdir(parents=True,exist_ok=True)
                with z.open(member) as src,dest.open('xb') as out:shutil.copyfileobj(src,out)

from project_analysis import ProjectAnalysis
from ui_tools import Interface
from office_forms import instruction

from interactions import Interactions

from save_decisions import SaveDecisions
from windows_integration import normal_window

from quality_library import QualityLibrary

from folder_operations import FolderOperations

class Studio(ProjectAnalysis,FolderOperations,SaveDecisions,QualityLibrary,Interactions,Interface,Workspace):
    def __init__(self,root):
        # Defer editor creation until a project is selected.
        self.root=root;self.project=None;self.sessions={};self.current=None;self.journals={};self.stopping=False;self.expanded={0:set(),3:set()}
        root.protocol("WM_DELETE_WINDOW",self.close);normal_window(root)
        PROJECTS.mkdir(parents=True,exist_ok=True);LIB.mkdir(parents=True,exist_ok=True)
        self.filters={};self.search_history={};self.search_redo={};self.saved_rev={};self.history={};self.redo={};self.replaying=False;self.targets={};self.selected={};self.buttons=[]
        self.saved_text=STORE/'Библиотека'/'Исключения.json'
        self.variants=json.loads(self.saved_text.read_text('utf-8')) if self.saved_text.exists() else {}
        from template_library import organize
        organize(LIB,SAMPLES.parent/'Шаблоны')
        root.title('Бюро ИД · Проекты');root.geometry('1380x820');root.configure(bg=BG)
        self.ui_init(STORE);self.row_choice={}
        self.home()
    def glass(self,target):
        # Layered, tinted surface with a fine highlight; independent of Windows theme.
        c=tk.Canvas(target,height=52,highlightthickness=0,bg='#eee1da');c.pack(fill='x')
        def paint(e):
            c.delete('all')
            for y in range(52):
                a=y/51
                ends=((64,62,66),(41,40,44)) if self.dark else ((255,251,248),(234,215,205))
                rgb=[int(v*(1-a)+w*a) for v,w in zip(*ends)]
                c.create_line(0,y,e.width,y,fill='#%02x%02x%02x'%tuple(rgb))
            c.create_line(0,1,e.width,1,fill='white')
            c.create_text(18,26,text='Бюро ИД',anchor='w',fill=self.colors['text'],font=('Segoe UI',17,'bold'))
            c.create_text(145,28,text=self.project.name if self.project else 'Рабочее пространство',anchor='w',fill=self.colors['muted'],font=('Segoe UI',11))
        c.bind('<Configure>',paint);self.glass_widgets=[w for w in getattr(self,'glass_widgets',[]) if w.winfo_exists()]+[c];return c
    def home(self,_approved=False):
        if getattr(self,'stopping',False):self.root.after(120,lambda:self.home(_approved));return
        if not _approved and self.project and hasattr(self,"models"):
            self.decide_project(lambda:self.home(True));return
        if getattr(self,'split',None) and self.split.winfo_exists():
            self.split.pack_forget();self.header.pack_forget()
            for n in list(self.windows):self.dock(n)
        if getattr(self,'landing',None) and self.landing.winfo_exists():self.landing.destroy()
        self.landing=tk.Frame(self.root,bg=BG);self.landing.pack(fill='both',expand=True)
        self.commands(self.landing)
        self.toolbar(self.landing,3)
        landing_split=tk.PanedWindow(self.landing,orient='horizontal',sashwidth=7,bg=self.colors['line'],showhandle=True);landing_split.pack(fill='both',expand=True)
        sidebar=tk.Frame(landing_split,bg=PAPER);landing_split.add(sidebar,width=310,minsize=175,stretch='never')
        right=tk.Frame(landing_split,bg=BG);landing_split.add(right,minsize=350,stretch='always')
        tk.Label(sidebar,text='Мои проекты',bg=PAPER,font=('Segoe UI',13,'bold')).pack(anchor='w',padx=18,pady=(20,6))
        projects=self.recent_list(PROJECTS)
        for project in projects:
            missing=not (project/'project.json').is_file()
            btn=ttk.Button(sidebar,text=project.name+(' · Данный проект отсутствует' if missing else ''),command=lambda p=project:self.enter(p))
            btn.recent_project=project;btn.pack(fill='x',padx=12,pady=2)
        if not projects:ttk.Label(sidebar,text='Пока нет недавних проектов',padding=12).pack(anchor='w')
        ttk.Button(sidebar,text='Все проекты…',command=lambda:self.project_browser(PROJECTS)).pack(padx=12,pady=8,anchor='w')
        tk.Label(sidebar,text='Библиотека документов',bg=PAPER,font=('Segoe UI',12,'bold')).pack(anchor='w',padx=18,pady=12)
        self.library_tree(sidebar,True)
        self.scan_card(right)
        center=tk.Frame(right,bg=BG);center.pack(expand=True,fill='both',padx=40,pady=40)
        tk.Label(center,text='Создать проект',bg=BG,font=('Segoe UI',24,'bold')).pack(anchor='w')
        tk.Label(center,text='Выберите источник документов',bg=BG,font=('Segoe UI',12)).pack(anchor='w',pady=16)
        self.source_zone(center)
        self.home_layout=(landing_split,sidebar,right,center)
        self._home_layout_pending=False
        def constrain(event=None):
            if event is not None and event.widget not in (landing_split,self.landing):return
            if self._home_layout_pending:return
            self._home_layout_pending=True
            def apply():
                self._home_layout_pending=False
                self.limit_home_layout()
            self.root.after_idle(apply)
        landing_split.bind('<Configure>',constrain,add='+')
        landing_split.bind('<B1-Motion>',lambda e:constrain(),add='+')
        landing_split.bind('<ButtonRelease-1>',lambda e:constrain(),add='+')
        self.root.after_idle(self.limit_home_layout)
        self.paint(self.landing)
    def import_item(self,kind,path=None,_approved=False):
        if not _approved and self.project and hasattr(self,"models"):
            self.decide_project(lambda:self.import_item(kind,path,True));return
        if path is None:
            if kind=='folder':value=filedialog.askdirectory()
            else:value=filedialog.askopenfilename(filetypes=[('Документы','*.xlsx *.xls *.docx *.doc')] if kind=='file' else [('Архив ZIP','*.zip')])
            if not value:return
            path=Path(value)
        dest=next_path(PROJECTS/path.stem);inputs=dest/'Документы'
        try:
            if path.is_dir() and (STORE.resolve().is_relative_to(path.resolve()) or path.resolve().is_relative_to(PROJECTS.resolve())):
                raise ValueError('Выберите исходную папку документов. Сохранённые проекты доступны слева.')
            inputs.mkdir(parents=True)
            if kind=='zip':unpack(path,inputs)
            elif kind=='folder':shutil.copytree(path,inputs,dirs_exist_ok=True)
            else:shutil.copy2(path,inputs/path.name)
            if not docs(inputs):raise ValueError('В источнике нет документов Word или Excel.')
            write_json(dest/'project.json',{'name':dest.name,'version':1,'source':str(path.resolve())})
        except Exception as e:
            shutil.rmtree(dest,ignore_errors=True);messagebox.showerror('Импорт',str(e));return
        self.analyze_import(dest,lambda:self.enter(dest))
    def enter(self,project,_approved=False):
        if getattr(self,'stopping',False):self.root.after(120,lambda:self.enter(project,_approved));return
        if not _approved and self.project and self.project!=project and hasattr(self,"models"):
            self.decide_project(lambda:self.enter(project,True));return
        if not (project/'project.json').is_file():
            messagebox.showinfo('Мои проекты','Данный проект отсутствует.');return
        if project not in self.journals and (project/'.recovery/state.json').exists():
            answer=messagebox.askyesnocancel('Восстановление','Обнаружена незавершённая работа. Восстановить её?\nДа — продолжить; Нет — вернуть состояние до сеанса; Отмена — не открывать проект.')
            if answer is None:return
            if not answer:
                from save_decisions import ProjectJournal
                previous=ProjectJournal(project);previous.restore();previous.temp.cleanup()
        self.touch_recent(project)
        first=not hasattr(self,'split')
        self.project=project;self.reference_path=None;self.journal();self.landing.pack_forget();self.selected.clear();self.expanded={0:set(),3:set()}
        paths=docs(project/'Документы')
        if first:
            # Base constructor uses the sample paths; intercept its initial open.
            self.initializing=True
            super().__init__(self.root)
            self.initializing=False
            self.split.forget(self.holders[0])
            left=tk.PanedWindow(self.split,orient='vertical',sashwidth=5,bg='#ddcfc6')
            self.split.add(left,before=self.holders[1],width=304,minsize=296)
            for n in (0,3):
                host=tk.Frame(left,bg=BG);left.add(host,minsize=100,stretch='always');self.holders[n]=host
            for c in self.header.winfo_children():c.destroy()
            self.commands(self.header)
            for w in ('<KeyPress>',):
                self.root.bind_class('IDCommands',w,self.keypress)
        else:
            self.header.pack(fill='x',before=self.split) if self.split.winfo_manager() else self.header.pack(fill='x')
            self.split.pack(fill='both',expand=True)
        self.paths=paths;self.current=None
        for n in range(4):self.build(n)
        self.set_palette();self.paint(self.root)
        if paths:self.open(paths[0])
        self.root.after(600,lambda p=project:self.ensure_project_passports(p))
    def open(self,path,_approved=False):
        if getattr(self,'stopping',False):self.root.after(120,lambda:self.open(path,_approved));return
        if path.suffix.lower()=='.pdf':self.show_reference(path);return
        if getattr(self,'reference_path',None) and self.current and self.current.source==path:
            self.reference_path=None
            for n in (1,2):self.build(n)
            return
        if getattr(self,'initializing',False):return
        if not _approved and self.current and self.current.source!=path:
            self.decide_document(self.current,lambda:self.open(path,True));return
        if path.suffix.lower()=='.pdf':self.show_reference(path);return
        self.reference_path=None
        self.journal().protect(path)
        if getattr(self,'initializing',False):return
        if path not in self.sessions:self.sessions[path]=Session(path,self.events,work_file=self.journal().work_file(path))
        super().open(path)
        # Keep at most two warm Office sessions; do not accumulate one Excel/
        # Word process per document in a large project.
        idle=[s for s in self.sessions.values() if s is not self.current and s.source not in self.journal().dirty]
        for s in idle[:-1]:
            self.sessions.pop(s.source,None);s.tasks.put(None)
            if not hasattr(self,'retiring_sessions'):self.retiring_sessions=[]
            self.retiring_sessions.append(s)
            for store in (self.models,self.latest,self.revisions,self.saved_rev,self.history,self.redo):store.pop(s,None)
        self.retiring_sessions=[s for s in getattr(self,'retiring_sessions',[]) if s.thread.is_alive()]
    def import_passport_folder(self):
        path=filedialog.askdirectory(parent=self.root,title='Папка паспортов и сертификатов')
        if not path:return
        from scanner_ui import scanner
        files=[p for p in Path(path).rglob('*') if p.suffix.lower() in ('.pdf','.jpg','.jpeg','.zip') and not p.name.startswith('~$')]
        if not files:messagebox.showinfo('Паспорта','В папке нет PDF, JPEG или ZIP.');return
        scanner(self,files=files,destination=self.project/'Документы' if self.project else None)
    def show_reference(self,path):
        view=getattr(self,'reference_view',None)
        if getattr(self,'reference_path',None) and view is not None and view.winfo_exists():
            self.reference_path=path;self.reference_label.configure(text=path.name);view.show(path,0);return
        if self.current and self.current in self.pending:
            self.root.after_cancel(self.pending[self.current]);self.submit(self.current)
        self.reference_path=path
        for n in (1,2):self.build(n)
    def choose(self):
        f=filedialog.askopenfilename(filetypes=[('Word и Excel','*.xlsx *.xls *.doc *.docx')])
        if f:self.add_copy(Path(f))
    def add_copy(self,p,_approved=False):
        if getattr(self,'stopping',False):self.root.after(120,lambda:self.add_copy(p,_approved));return
        if not _approved and self.current and self.current.source in self.journal().dirty:
            self.decide_document(self.current,lambda:self.add_copy(p,True));return
        dest=next_path(self.project/'Документы'/p.name);shutil.copy2(p,dest)
        self.paths.append(dest);self.open(dest)
    def library_tree(self,parent,on_home=False):
        frame=ttk.Frame(parent);frame.pack(fill='both',expand=True,padx=4)
        tree=ttk.Treeview(frame,show='tree',height=10)
        tree.column('#0',minwidth=600,width=600,stretch=False)
        vert=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);horiz=ttk.Scrollbar(frame,orient='horizontal',command=tree.xview)
        tree.configure(yscrollcommand=vert.set,xscrollcommand=horiz.set)
        horiz.pack(side='bottom',fill='x');vert.pack(side='right',fill='y');tree.pack(fill='both',expand=True)
        paths=docs(LIB)
        for project in PROJECTS.iterdir():
            if (project/'project.json').is_file():paths.extend(docs(project/'Документы'))
        self.search_tree(tree,STORE,paths,3);self.drag_from_library(tree,on_home)
        def use():
            sel=tree.selection()
            if not sel or not tree.item(sel[0],'values'):return
            path=Path(tree.item(sel[0],'values')[0])
            if not path.is_file():return
            if on_home:self.import_item('file',path)
            else:self.add_copy(path)
        tree.bind('<<TreeviewSelect>>',lambda e:self.selected.update({3:self.tree_selection(tree)}))
        from app_dialogs import action
        actions=ttk.Frame(parent);actions.panel_toolbar=True;actions.pack(fill='x',padx=4,pady=4)
        tree.bind('<Double-1>',lambda e:use())
        if not on_home:action(self,actions,'Как шаблон','save',self.keep_template).pack(side='right',padx=2)
        action(self,actions,'Создать проект' if on_home else 'В проект','copy',use).pack(side='right',padx=2)
    def search_tree(self,tree,base,paths,n):
        tree.panel_id=n
        def remember(e):
            def capture():
                if not tree.winfo_exists():return
                def visit(parent=''):
                    for node in tree.get_children(parent):
                        if tree.get_children(node):
                            if tree.item(node,'open'):self.expanded[n].add(node)
                            else:self.expanded[n].discard(node)
                        visit(node)
                visit()
            tree.after_idle(capture)
        tree.bind('<<TreeviewOpen>>',remember);tree.bind('<<TreeviewClose>>',remember)
        var=tk.StringVar(value=self.filters.get(n,''))
        entry=ttk.Entry(tree.master,textvariable=var)
        entry.pack(fill='x',before=tree,padx=4,pady=3)
        def render(*args):
            text=var.get()
            old=self.filters.get(n,'')
            if old!=text and not self.replaying:
                self.search_history.setdefault(n,[]).append(old)
                self.search_redo[n]=[]
            self.filters[n]=text
            tree.delete(*tree.get_children())
            self.populate(tree,base,[p for p in paths if text.casefold() in str(p.relative_to(base)).casefold()])
        var.trace_add('write',render);render()
        self.targets[n]=entry
        entry.bind('<FocusIn>',lambda e:setattr(self,'active_panel',n))
        entry.bind('<KeyPress>',lambda e:self.panel_key(e,n))
        entry.bind('<MouseWheel>',lambda e:(tree.yview_scroll(-1 if e.delta>0 else 1,'units'),'break')[1])
        entry.bind('<Escape>',lambda e:tree.focus_set())
        tree.bind('<FocusIn>',lambda e:setattr(self,'active_panel',n))
        tree.bind('<KeyPress>',lambda e:self.panel_key(e,n))
    def panel_key(self,event,n):
        from clipboard_keys import operation
        op=operation(event)
        if op:
            self.command(n,op);return 'break'
    def populate(self,tree,base,paths):
        opened=self.expanded.get(getattr(tree,'panel_id',-1),set())
        root_id=str(base.resolve())
        nodes={base:tree.insert('','end',iid=root_id,text=base.name,values=(str(base),'folder'),open=root_id in opened)}
        folders=set()
        for path in paths:
            folders.update(p for p in path.parents if p!=base and p.is_relative_to(base))
        if getattr(tree,'panel_id',-1)==0 and not self.filters.get(0):
            folders.update(p for p in base.rglob('*') if p.is_dir())
        for folder in sorted(folders,key=lambda p:(len(p.parts),str(p).casefold())):
            if folder.parent in nodes:
                nodes[folder]=tree.insert(nodes[folder.parent],'end',iid=str(folder.resolve()),text='└─ '+folder.name,values=(str(folder),'folder'),open=str(folder.resolve()) in opened)
        tree.tag_configure('active',foreground=self.colors['text'],background=self.colors['sel'])
        for path in paths:
            tree.insert(nodes[path.parent],'end',text=('★ ' if self.current and path==self.current.source else '└─ ')+path.stem,values=(str(path),'file'),tags=('active',) if self.current and path==self.current.source else ())
        if tree.cget('xscrollcommand'):
            import tkinter.font as tkfont
            font=tkfont.Font(font=('Segoe UI',9))
            width=max((font.measure(p.name)+25*len(p.relative_to(base).parts)+64 for p in [*paths,*folders]),default=400)
            tree.column('#0',width=max(400,width),stretch=False,minwidth=100)
    @staticmethod
    def tree_selection(tree):
        sel=tree.selection()
        return str(tree.item(sel[0],'values')[0]) if sel and tree.item(sel[0],'values') else ''
    def tree(self):
        area=ttk.Frame(self.body[0]);area.pack(expand=True,fill='both')
        tree=ttk.Treeview(area,show='tree');tree.column('#0',width=650,stretch=False)
        sy=ttk.Scrollbar(area,orient='vertical',command=tree.yview);sx=ttk.Scrollbar(area,orient='horizontal',command=tree.xview)
        tree.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
        sx.pack(side='bottom',fill='x');sy.pack(side='right',fill='y');tree.pack(expand=True,fill='both')
        if not self.project:return
        self.search_tree(tree,self.project/'Документы',sorted(set(self.paths)|set((self.project/'Документы').rglob('*.pdf'))) if not getattr(self,'initializing',False) else [],0)
        def pick(e):
            value=self.tree_selection(tree);self.selected[0]=value
            if value and Path(value).is_file() and (getattr(self,'reference_path',None) or not self.current or Path(value)!=self.current.source):self.open(Path(value))
        tree.bind('<<TreeviewSelect>>',pick)
        tree.bind('<Button-3>',lambda e:self.document_context(tree,e));self.folder_drag(tree)
    def build(self,n):
        view=getattr(self,'pdf_viewer',None)
        if n==2 and not getattr(self,'reference_path',None) and self.current in getattr(self,'latest',{}) and view is not None and view.winfo_exists() and view.master is self.body.get(2) and self.body[2].master is self.windows.get(2,self.holders.get(2)):
            self.draw();return
        if n==1:self.release_form_variables()
        if n in getattr(self,'collapsed',set()):self.collapsed_dirty.add(n);return
        if n==3:
            host=self.windows.get(n,self.holders[n])
            for w in host.winfo_children():w.destroy()
            self.pane_header(n,host)
            self.toolbar(host,n)
            self.library_tree(host)
            self.paint(host);self.root.after_idle(self.enforce_panel_sizes);return
        super().build(n)
        host=self.windows.get(n,self.holders[n])
        if host.winfo_children():
            for btn in host.winfo_children()[0].winfo_children():btn.window_button=True
        self.root.after_idle(lambda: self.paint(self.windows.get(n,self.holders[n])) if n in self.holders else None)
        host=self.windows.get(n,self.holders[n]);self.toolbar(host,n,before=self.body[n]);self.root.after_idle(self.enforce_panel_sizes)
    def keep_template(self):
        if not self.current:return
        s=self.current
        from app_dialogs import ask_text
        title=ask_text(self,'Шаблон','Название шаблона',s.copy.stem)
        if not title:return
        if any(c in title for c in '<>:"/\\|?*') or title in ('.','..'):messagebox.showerror('Шаблон','Недопустимое имя');return
        from template_library import category
        dest=LIB/category(title+' '+s.copy.stem)/(title+s.copy.suffix)
        dest.parent.mkdir(exist_ok=True);dest=next_path(dest)
        def finish():
            if not s.thread.is_alive():
                messagebox.showerror('Шаблон','Документ не удалось сохранить.');return
            if s not in self.latest or self.saved_rev.get(s,-1)!=self.revisions[s]:
                self.root.after(200,finish);return
            shutil.copy2(s.copy,dest);self.build(3);self.status.set('Шаблон сохранён: '+str(dest))
        if not hasattr(self,'saved_rev'):self.saved_rev={}
        finish()
    def library_change(self,delete):
        path=Path(self.selected.get(3,''))
        if not path.is_file() or not path.resolve().is_relative_to(LIB.resolve()):
            messagebox.showinfo('Библиотека','Выберите файл в папке шаблонов.');return
        try:
            if delete:
                if not messagebox.askyesno('Удаление шаблона',f'Удалить шаблон «{path.name}»?'):return
                path.unlink()
            else:
                name=self.folder_name(path.name)
                if not name:return
                target=path.with_name(name)
                if not target.suffix:target=target.with_suffix(path.suffix)
                if target==path:return
                if target.exists():raise ValueError('Такое имя уже существует.')
                path.rename(target);self.selected[3]=str(target)
            self.build(3)
        except (OSError,ValueError) as e:messagebox.showerror('Библиотека',str(e))
    def toolbar(self,host,n,before=None,inline=False):
        if n==1 and getattr(self,'reference_path',None):return
        if n==2:return
        line=tk.Frame(host,bg='#f6eee8');line.panel_toolbar=True;line.pack(**({'side':'left'} if inline else {'fill':'x'}),**({'before':before} if before else {}))
        for key,label in [('undo','Отменить · Ctrl+Z'),('redo','Повторить · Ctrl+Y'),('cut','Вырезать · Ctrl+X'),('copy','Копировать · Ctrl+C'),('paste','Вставить · Ctrl+V')]:
            self.icon_button(line,key,label,lambda k=key:self.command(n,k))
        if n in (0,None):
            self.icon_button(line,'passports','Добавить папку паспортов и сертификатов',self.import_passport_folder)
            self.icon_button(line,'folder','Создать папку в выбранной ветви проекта',self.new_folder)
            self.icon_button(line,'close','Закрыть текущий документ с выбором сохранения',self.close_document)
            self.icon_button(line,'delete','Удалить выбранный документ из проекта',self.delete_document)
        if n==3:
            self.icon_button(line,'rename','Переименовать выбранный шаблон',lambda:self.library_change(False))
            self.icon_button(line,'delete','Удалить выбранный шаблон',lambda:self.library_change(True))
        if n==1:
            self.icon_button(line,'link','Назначить дополнительное поле неизвестной формы',lambda:__import__('manual_fields').dialog(self))
            if getattr(self.current,'analysis',None):self.icon_button(line,'help','Проверить распознанные поля и замечания',self.review_word_fields)
            self.icon_button(line,'exception','Сохранить введённый вариант как исключение',self.save_exception)
            if 'titleAddress' in self.models.get(self.current,{}):
                self.icon_button(line,'import','Заполнить титул данными выбранного акта проекта',self.title_from_act)
            if self.current in getattr(self,'row_actions',{}):
                insert,catalog,remove=self.row_actions[self.current]
                actions=tk.Frame(host,bg='#f6eee8');actions.panel_toolbar=True
                actions.pack(fill='x',**({'before':before} if before else {}))
                self.icon_button(actions,'addrow','Добавить указанное количество строк после текущей позиции, перед следующей шапкой',insert)
                self.icon_button(actions,'deleterow','Удалить указанное количество строк после текущей позиции до следующей шапки. Заголовки сохраняются',remove)
                self.icon_button(actions,'catalog','Заполнить текущую строку из каталога документов',catalog)
                if any(k.startswith('part') for k in self.models.get(self.current,{})):
                    self.icon_button(actions,'addsection','Добавить раздел по образцу текущего',lambda:self.register_section(False))
                    self.icon_button(actions,'deletesection','Удалить текущий раздел со всеми его позициями',lambda:self.register_section(True))
    def command(self,n,cmd):
        if n is None:
            n=getattr(self,'active_panel',1)
        if n==2:
            if cmd=='copy' and getattr(self,'preview_selection',None):
                self.preview_selection.copy()
            return
        if n==0:
            focus=self.root.focus_get()
            if isinstance(focus,ttk.Treeview):
                if cmd in ('copy','cut'):self.file_clipboard(cmd=='cut');return
                if cmd=='paste':self.paste_document();return
            if cmd=='paste' and getattr(self,'path_clipboard',None):self.paste_document();return
        if n in (0,3):
            entry=self.targets.get(n)
            if not entry or not entry.winfo_exists():return
            if cmd=='copy' and not entry.selection_present() and self.selected.get(n):
                self.root.clipboard_clear();self.root.clipboard_append(self.selected[n]);return
            entry.focus_set()
            if cmd in ('undo','redo'):
                h,r=(self.search_history,self.search_redo) if cmd=='undo' else (self.search_redo,self.search_history)
                stack=h.get(n,[])
                if stack:
                    value=stack.pop();r.setdefault(n,[]).append(entry.get());self.replaying=True
                    try:entry.setvar(entry.cget('textvariable'),value)
                    finally:self.replaying=False
            elif cmd=='all':entry.selection_range(0,'end')
            else:entry.event_generate({'cut':'<<Cut>>','copy':'<<Copy>>','paste':'<<Paste>>'}[cmd])
            return
        widget=self.targets.get(1)
        if not widget or not widget.winfo_exists():return
        widget.focus_set()
        if cmd in ('undo','redo'):
            h=self.history if cmd=='undo' else self.redo;r=self.redo if cmd=='undo' else self.history
            entries=h.get(self.current,[])
            if not entries:return
            key,old,new=entries.pop();r.setdefault(self.current,[]).append((key,old,new))
            self.replaying=True
            try:
                if key not in self.views and key.startswith('row'):
                    self.row_choice[self.current]=int(key.split('_')[0][3:]);self.build(1)
                self.views[key].set(old if cmd=='undo' else new)
            finally:self.replaying=False
        elif cmd=='all':widget.selection_range(0,'end')
        else:widget.event_generate({'cut':'<<Cut>>','copy':'<<Copy>>','paste':'<<Paste>>','all':'<<SelectAll>>'}[cmd])
    def keypress(self,e):
        from clipboard_keys import operation
        op=operation(e)
        if op:
            self.command(1,op);return 'break'
    def form(self):
        self.append_popup={}
        if self.current and getattr(self.current,'row_operation_busy',False):
            getattr(self,'row_actions',{}).pop(self.current,None)
            self.views={};self.targets.pop(1,None)
            ttk.Label(self.body[1],text='Обновляем строки реестра…',padding=16).pack(anchor='w')
            return
        if getattr(self,'reference_path',None):
            ttk.Label(self.body[1],text='Просмотр схемы. Поля текущего документа сохранены временно. Вернитесь к акту для продолжения.',wraplength=320,padding=12).pack();return
        super().form()
        self.root.after_idle(lambda:self.paint(self.body[1]) if self.body[1].winfo_exists() else None)
        if not self.current or self.current not in self.models:return
        var_keys={str(v):k for k,v in self.views.items()}
        def scan(w):
            if isinstance(w,(ttk.Entry,ttk.Combobox)):
                key=var_keys.get(str(w.cget('textvariable')))
                if not key:return
                w.bindtags(('IDCommands',)+w.bindtags())
                w.bind('<FocusIn>',lambda e:self.focus_field(e.widget))
                from drag_selection import install
                install(w)
                if isinstance(w,ttk.Combobox) and key in ('materials','schemes','project','attachments','hiddenWorks'):
                    def post(k=key,v=self.views[key]):
                        self.append_popup[k]={'before':v.get(),'active':True}
                    def chosen(e,k=key,v=self.views[key]):
                        from quality_library import reference_text
                        selected=reference_text(v.get().strip());previous=self.append_popup.pop(k,{}).get('before',self.models[self.current].get(k,'')).strip()
                        if previous in ('','-'):text=selected
                        elif previous==selected or previous.endswith(', '+selected):text=previous
                        else:text=previous.rstrip(', ') + ', ' + selected
                        v.set(text)
                        widget=e.widget;widget.focus_set();widget.icursor('end');widget.xview('end')
                        start=len(text)-len(selected) if text.endswith(selected) else 0
                        widget.selection_range(start,len(text))
                    w.preserve_segment_selection=True
                    w.configure(postcommand=post);w.bind('<<ComboboxSelected>>',chosen,add='+')
                    pop=w.tk.call('ttk::combobox::PopdownWindow',str(w))
                    def unpost(k=key):
                        def clear():
                            if k in self.append_popup:self.append_popup[k]['active']=False
                        self.root.after_idle(clear)
                    command=w.register(unpost)
                    w.tk.call('bind',pop,'<Unmap>',command)

                if isinstance(w,ttk.Combobox):
                    if key not in ('materials','schemes','project','attachments','hiddenWorks'):
                        def focus_insert(e):
                            widget=e.widget;widget.focus_set();widget.icursor('end');widget.selection_range(0,'end');widget.xview('end')
                        w.bind('<<ComboboxSelected>>',focus_insert,add='+')
                    vals=[v for v in dict.fromkeys([*w.cget('values'),*self.variants.get(key,[]),*self.quality_choices(key)]) if not instruction(v)];w.configure(values=vals)
                if key in ('address','number','start','workStart','clientSign','developerSign'):
                    group={'address':'Общие данные проекта','number':'Акт и участники','start':'Даты работ','workStart':'Даты работ','clientSign':'Подписи','developerSign':'Подписи'}[key]
                    children=w.master.winfo_children();previous=children[children.index(w)-1]
                    ttk.Label(w.master,text=group,font=('Segoe UI',10,'bold')).pack(before=previous,anchor='w',padx=12,pady=(12,1))
                var=self.views[key];state=[var.get()]
                def track(*args):
                    if self.append_popup.get(key,{}).get('active'):return
                    new=var.get()
                    if isinstance(w,ttk.Combobox):
                        query=new.strip().casefold()
                        current_choices=list(dict.fromkeys([*vals,*self.quality_choices(key)]))
                        choices=sorted(current_choices,key=lambda v:(not v.casefold().startswith(query),query not in v.casefold())) if query else current_choices
                        w.configure(values=choices)
                    if not self.replaying and not getattr(self,'following',False) and state[0]!=new:
                        self.history.setdefault(self.current,[]).append((key,state[0],new))
                        self.redo[self.current]=[]
                    state[0]=new
                var.trace_add('write',track)
            for child in w.winfo_children():scan(child)
        scan(self.body[1]);self.form_mouse(self.body[1])
    def visible_fields(self,session,vals,parent):
        if not hasattr(self,'row_actions'):self.row_actions={}
        self.row_actions.pop(session,None)
        rows=sorted({int(k.split('_')[0][3:]) for k in vals if k.startswith('row')})
        if not rows:
            return vals
        active=self.row_choice.get(session,rows[0])
        if active not in rows:active=min(rows,key=lambda r:abs(r-active))
        self.row_choice[session]=active
        line=ttk.Frame(parent);line.pack(fill='x',padx=10)
        ttk.Label(line,text='Строка реестра').pack(side='left')
        selector=ttk.Combobox(line,values=rows,state='readonly',width=8);selector.set(active);selector.pack(side='left')
        def select(e):
            row=int(selector.get());self.row_choice[session]=row;self.build(1);self.request_review(session,row=row)
        selector.bind('<<ComboboxSelected>>',select)
        def insert():
            count=simpledialog.askinteger('Добавление позиций','Сколько строк добавить после текущей позиции?',initialvalue=1,minvalue=1,maxvalue=500,parent=self.root)
            if count:self.queue_register_operation(session,False,dict(rows=[active],count=count,after=True))
        def remove():
            count=simpledialog.askinteger('Удаление позиций','Сколько строк удалить после текущей позиции? Шапка следующего раздела сохраняется.',initialvalue=1,minvalue=1,parent=self.root)
            if not count:return
            from register_selection import following_rows
            selected,available=following_rows(vals,active,count)
            if not selected:
                messagebox.showinfo('Удаление позиций','После текущей позиции до следующей шапки строк нет.');return
            notice=f'В разделе нет {count} строк после текущей позиции. Удалено строк: {len(selected)} — до следующей шапки.' if count>available else ''
            self.queue_register_operation(session,True,dict(rows=selected,notice=notice))
        self.row_actions[session]=(insert,lambda:self.catalog_into_row(session,active),remove)
        parts=[k for k in vals if k.startswith('part') and k[4:].isdigit() and int(k[4:])<=active]
        nearest=max(parts,key=lambda k:int(k[4:])) if parts else None
        groups=[k for k in vals if k.startswith('group') and k[5:].isdigit() and int(k[5:])<=active and (nearest is None or int(k[5:])>=int(nearest[4:]))]
        nearest_group=max(groups,key=lambda k:int(k[5:])) if groups else None
        return {k:v for k,v in vals.items() if (not k.startswith('row') or k.startswith(f'row{active}_')) and (not k.startswith('part') or k==nearest) and (not k.startswith('group') or k==nearest_group)}
    def register_section(self,delete):
        s=self.current;vals=self.models.get(s,{})
        row=self.row_choice.get(s,0)
        parts=sorted(int(k[4:]) for k in vals if k.startswith('part') and k[4:].isdigit())
        start=max((r for r in parts if r<=row),default=None)
        if start is None:return
        end=next((r for r in parts if r>start),10**9)
        count=len({int(k.split('_')[0][3:]) for k in vals if k.startswith('row') and start<int(k.split('_')[0][3:])<end})
        name=vals['part'+str(start)]
        if delete:
            if len(parts)<2:
                messagebox.showinfo('Раздел','Последний раздел нужно сохранить. Можно удалить его позиции.',parent=self.root);return
            if not messagebox.askyesno('Удаление раздела',f'Удалить раздел «{name}» и его позиции ({count})?',parent=self.root):return
            title=''
        else:
            title=simpledialog.askstring('Новый раздел','Название раздела:',parent=self.root)
            if not title or not title.strip():return
        self.queue_register_operation(s,delete,dict(section=start,title=title))
    def queue_register_operation(self,session,delete,options=None):
        if getattr(self,'stopping',False):return
        queue=getattr(session,'row_operations',None)
        if queue is None:queue=[];session.row_operations=queue
        queue.append(dict(delete=delete,**options) if options else delete)
        self.start_register_operation(session)
    def start_register_operation(self,session):
        if getattr(session,'row_operation_busy',False) or not getattr(session,'row_operations',[]):return
        if self.sessions.get(session.source) is not session:return
        if not session.thread.is_alive():
            session.row_operations.clear();messagebox.showerror('Реестр','Редактор документа завершился. Откройте документ повторно.');return
        rows=sorted({int(k.split('_')[0][3:]) for k in self.models.get(session,{}) if k.startswith('row')})
        if not rows:session.row_operations.clear();return
        row=self.row_choice.get(session,rows[0]);row=min(rows,key=lambda n:abs(n-row))
        if session in self.pending:
            self.root.after_cancel(self.pending[session]);self.submit(session)
        operation=session.row_operations.pop(0)
        options=operation if isinstance(operation,dict) else dict(delete=operation)
        delete=options['delete'];session.row_operation_busy=True
        self.revisions[session]+=1;self.mark_changed(session)
        session.tasks.put(dict(row=row,revision=self.revisions[session],**options))
        self.status.set('Удаляем позицию и пересчитываем реестр…' if delete else 'Добавляем позицию и пересчитываем реестр…')
        if session is self.current:self.build(1)
    def title_from_act(self):
        import re
        s=self.current
        candidates=[other for other,m in self.models.items() if other.source.is_relative_to(self.project) and 'address' in m and 'project' in m]
        if not candidates:messagebox.showinfo('Титул','Сначала откройте нужный акт проекта.');return
        win=tk.Toplevel(self.root);win.title('Источник данных титула');win.geometry('560x320')
        from app_dialogs import action
        action(self,win,'Применить','paste',lambda:use()).pack(side='bottom',anchor='e',padx=12,pady=10)
        box=tk.Listbox(win,exportselection=False);box.pack(fill='both',expand=True,padx=12,pady=12)
        for other in candidates:box.insert('end',other.source.stem)
        box.selection_set(0)
        def use():
            if self.current is not s or not box.curselection():return
            other=candidates[box.curselection()[0]]
            m=self.models[other];vals={'titleAddress':m.get('address',''),'titleClient':m.get('client','')}
            codes=re.findall(r'шифр\s+([^\s;,]+)',m.get('project',''),re.I)
            vals.update({f'code{i}':v for i,v in enumerate(dict.fromkeys(codes),1)})
            for key,val in vals.items():
                if val and key in self.views:self.views[key].set(val)
            win.destroy()
        box.bind('<Double-1>',lambda e:use())
        self.paint(win);win.transient(self.root);win.grab_set()
    def catalog_into_row(self,s,row):
        file=self.catalog_dir/'Документы качества.json'
        items=json.loads(file.read_text('utf-8')) if file.exists() else []
        if not items:messagebox.showinfo('Каталог','Сначала разберите паспорта на главной странице.');return
        win=tk.Toplevel(self.root);win.title('Документ качества для строки '+str(row));win.geometry('660x370')
        from app_dialogs import action
        action(self,win,'Заполнить строку','paste',lambda:use()).pack(side='bottom',anchor='e',padx=12,pady=10)
        body=ttk.Frame(win);body.pack(fill='both',expand=True,padx=12,pady=8)
        box=tk.Listbox(body,exportselection=False)
        scroll=ttk.Scrollbar(body,command=box.yview);scroll.pack(side='right',fill='y')
        box.configure(yscrollcommand=scroll.set);box.pack(fill='both',expand=True)
        for m in items:box.insert('end',f"{m['type']}  {m['number']}  {m['date']}  {m['material']}")
        def use():
            if self.current is not s or not box.curselection():return
            m=items[box.curselection()[0]]
            vals={'Материал':m['material'],'Вид документа':m['type'],'Наименование документа':m['type'],
                  'Номер':m['number'] or 'б/н','Номер документа':m['number'] or 'б/н','Дата':m['date'],
                  'Количество листов':str(m['end']-m['start']+1)}
            if not m['number'] and not m['date']:
                vals.update({'Вид документа':m['material'],'Наименование документа':m['material'],'Номер':'','Номер документа':''})
            for k,v in self.views.items():
                if k.startswith(f'row{row}_') and s.labels[k] in vals:v.set(vals[s.labels[k]])
            win.destroy()
        self.paint(win);win.transient(self.root);win.grab_set()
    def focus_field(self,w):
        self.targets[1]=w;self.active_panel=1
        key=next((k for k,v in self.views.items() if str(v)==str(w.cget('textvariable'))),'')
        self.request_review(self.current,key=key)
    def request_review(self,session,key='',row=0):
        if not session or session not in self.models:return
        if key.startswith('row'):row=int(key.split('_')[0][3:])
        context=dict(activeKey=key,activeRow=row)
        if session.preview_context==context:return
        session.preview_context=context
        old=getattr(session,'review_timer',None)
        if old is not None:
            try:self.root.after_cancel(old)
            except tk.TclError:pass
        def refresh():
            session.review_timer=None
            if getattr(self,'stopping',False) or self.sessions.get(session.source) is not session:return
            # Focus changes do not alter document revisions or the save decision.
            if session not in self.pending:Workspace.submit(self,session)
        session.review_timer=self.root.after(160,refresh)
    def changed(self,s,key,v):
        if getattr(self,'append_popup',{}).get(key,{}).get('active'):return
        before=self.revisions[s]
        super().changed(s,key,v)
        if self.revisions[s]!=before:
            view=getattr(self,'pdf_viewer',None)
            if s is self.current and not getattr(self,'reference_path',None) and view is not None and view.winfo_exists() and view.quick_field(key,v):
                self.root.after_cancel(self.pending[s]);self.pending[s]=self.root.after(900,lambda:self.submit(s))
            j=self.journal();j.dirty.add(s.source)
            j.drafts[str(s.source.relative_to(j.base))]=dict(self.models[s])
            from recovery_state import persist
            old=getattr(j,'persist_job',None)
            if old is not None:self.root.after_cancel(old)
            def checkpoint():
                j.persist_job=None
                if self.journals.get(j.project) is j:persist(j)
            j.persist_job=self.root.after(300,checkpoint)
    def submit(self,s):
        super().submit(s)
        self.mark_changed(s)
    def save_exception(self):
        s=self.current;widget=self.targets.get(1)
        if not s or not widget or not widget.winfo_exists():return
        key=next((k for k,v in self.views.items() if str(v)==str(widget.cget('textvariable'))),None)
        if not key:return
        value=widget.get().strip()
        if not value or instruction(value):return
        if value not in self.variants.setdefault(key,[]):self.variants[key].append(value)
        write_json(self.saved_text,self.variants)
        if isinstance(widget,ttk.Combobox):widget.configure(values=self.variants[key])
        self.status.set('Исключение сохранено для этого поля.')
    def mark_changed(self,s):
        j=self.journal();j.dirty.add(s.source)
        from recovery_state import persist
        persist(j)
        if self.project and s.source.is_relative_to(self.project):
            mf=self.project/'project.json';meta=json.loads(mf.read_text('utf-8'));edited=set(meta.get('edited',[]))
            edited.add(str(s.source.relative_to(self.project)));meta['edited']=sorted(edited);write_json(mf,meta)
