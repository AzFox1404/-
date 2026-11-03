"""Desktop preview prototype. Office edits a copy and supplies the printed pages."""
from smooth_scrollbar import Scrollbar
import itertools
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import uuid
import tkinter as tk
from tkinter import ttk, filedialog
from app_dialogs import messagebox
from datetime import datetime
from PIL import ImageTk
import pypdfium2 as pdfium

from app_paths import ROOT, APP_DIR, EXAMPLES_ROOT
SAMPLES = EXAMPLES_ROOT / '1. КМ'
NAMES = ['Документы', 'Заполнение', 'Предпросмотр PDF']
LABELS = dict(work='Наименование работ', address1='Объект и адрес · первая строка',
              address2='Адрес · продолжение', start='Начало работ', end='Окончание работ',
              date='Дата акта', developer='Фамилия, имя, отчество представителя застройщика',
              foreman='Фамилия и инициалы производителя работ')
DATES = {'start','end','date'}
BG, PAPER, ACCENT = '#faf5f1','#fffdfa','#eac7b4'


class Session:
    def __init__(self, path, events, prepared=False, work_file=None):
        self.source = path
        directory = ROOT / 'Рабочие копии' / uuid.uuid4().hex[:10]
        if not prepared and not work_file: directory.mkdir(parents=True)
        self.copy = Path(work_file) if work_file else path if prepared else directory / path.name
        if work_file:self.copy.parent.mkdir(parents=True,exist_ok=True)
        if self.copy!=path and not self.copy.exists():shutil.copyfile(path,self.copy)
        import tempfile
        self.preview_dir=Path(tempfile.mkdtemp(prefix='bureau-preview-'))
        self.events = events
        self.tasks = queue.Queue()
        self.preview_context={};self.review_pdf=None
        self.structural_review=False
        self.validated_revision=-1;self.formula_errors=[];self.clean_hash=None;self.verified_values=None;self.timings=[]
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        process = None
        try:
            import time
            started=time.perf_counter()
            from final_pdf_cache import FinalPDFCache,digest
            cached=FinalPDFCache().get(self.source)
            if cached:self.events.put((self,'clean',(0,cached)))
            from office_forms import extra_fields
            from act_layout import act_rows
            prepared=None
            if self.copy.suffix.lower() in ('.doc','.docx'):
                from word_fields import prepare_word
                from project_analysis import preferred_word_plan,save_word_plan
                plan=preferred_word_plan(self.copy)
                if not plan:
                    try:
                        if self.copy.read_bytes()==self.source.read_bytes():plan=preferred_word_plan(self.source)
                    except OSError:pass # source can be renamed while opening
                plan=plan or prepare_word(self.copy,self.preview_dir/'word');spec=plan['fields'];prepared=plan['prepared'];self.analysis=plan
            else:spec=extra_fields(self.copy)
            self.spec=spec;self.labels={k:v['label'] for k,v in spec.items()}
            mapfile=self.preview_dir/'Карта.json'
            mapfile.write_text(json.dumps(spec,ensure_ascii=False),'utf-8')
            layoutfile=self.preview_dir/'layout.json';layoutfile.write_text(json.dumps(act_rows(self.copy),ensure_ascii=False),'utf-8')
            process = subprocess.Popen(['powershell.exe','-NoProfile','-STA','-ExecutionPolicy','Bypass',
                '-File',str(APP_DIR/'PreviewWorker.ps1'),'-WorkFile',str(self.copy),'-FieldMap',str(mapfile),'-ActLayout',str(layoutfile),*(['-PreparedFile',prepared] if prepared else [])],
                encoding='utf-8',stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW)
            def receive():
                line = process.stdout.readline()
                if not line:
                    raise RuntimeError(process.stderr.read() or 'Редактор Office завершился.')
                response = json.loads(line.lstrip(chr(0xfeff)))
                if 'error' in response:
                    raise RuntimeError(response['error'])
                return response
            ready=receive();fields=ready['fields'];self.register_repaired=bool(ready.get('registerRepaired'))
            if self.register_repaired:
                spec=extra_fields(self.copy)
                process.stdin.write(json.dumps({'reload':spec})+'\n');process.stdin.flush()
                fields=receive()['fields'];self.spec=spec;self.labels={k:v['label'] for k,v in spec.items()}
            from manual_fields import rules as manual_rules
            self.labels.update({k:manual_rules().get('_names',{}).get(k,k) for k in fields if k.startswith('ID_User_')})
            baseline=dict(fields)
            self.events.put((self,'fields',fields))
            empty=object();held=empty
            for serial in itertools.count():
                if serial:
                    job=self.tasks.get() if held is empty else held;held=empty
                    if isinstance(job,tuple):
                        while True:
                            try:newer=self.tasks.get_nowait()
                            except queue.Empty:break
                            if isinstance(newer,tuple):job=newer
                            else:held=newer;break
                    if job is None: break
                    started=time.perf_counter()
                    if isinstance(job,dict):
                        process.stdin.write(json.dumps(dict(batch=job))+'\n');process.stdin.flush();response=receive();inserted_row=response.get('row',job['row']+1)
                        if self.copy.suffix.lower() in ('.doc','.docx'):
                            spec=response['spec'];fields=response['fields']
                        else:
                            spec=extra_fields(self.copy)
                            process.stdin.write(json.dumps({'reload':spec})+'\n');process.stdin.flush()
                            fields=receive()['fields']
                        self.spec=spec;self.labels={k:v['label'] for k,v in spec.items()};revision=job['revision']
                        # Row coordinates changed, not the text in shifted cells.
                        # Rebase comparisons so a structural edit only marks totals.
                        baseline=dict(fields);self.structural_review=True
                        candidates=sorted({int(k.split('_')[0][3:]) for k in fields if k.startswith('row')})
                        preferred=job['row'] if job.get('delete') else inserted_row
                        selected=min(candidates,key=lambda n:abs(n-preferred)) if candidates else 0
                        self.preview_context=dict(activeKey='',activeRow=selected)
                        self.events.put((self,'rows',(fields,selected)))
                        if job.get('notice'):self.events.put((self,'notice',job['notice']))
                    else:
                        fields, revision = job
                else: revision = 0
                pdf = self.preview_dir / 'Предпросмотр.pdf'
                review=self.preview_dir/'Разметка.pdf'
                changed=[k for k,v in fields.items() if v!=baseline.get(k,'')]
                context=dict(self.preview_context)
                process.stdin.write(json.dumps(dict(values=fields,pdf=str(pdf),reviewPdf=str(review),changedKeys=changed,structuralReview=self.structural_review,**context))+'\n')
                process.stdin.flush()
                response=receive()
                if response.get('cleanReady'):
                    self.guides=response.get('guides',{})
                    from pdf_guide_scale import calibrate
                    self.guides=calibrate(self.guides,pdf.read_bytes())
                    data=pdf.read_bytes();self.clean_hash=digest(self.copy)
                    self.formula_errors=response.get('formulaErrors',[]);self.validated_revision=revision
                    self.verified_values=(revision,dict(fields))
                    self.timings.append(dict(revision=revision,clean_ms=round((time.perf_counter()-started)*1000)))
                    self.timings=self.timings[-32:]
                    self.events.put((self,'clean',(revision,data)))
                    response=receive()
                    self.timings[-1]['review_ms']=round((time.perf_counter()-started)*1000)-self.timings[-1]['clean_ms']
                started=time.perf_counter()
                self.review_pdf=(revision,review.read_bytes()) if response.get('hasReview') else None
                if hasattr(self,'analysis'):save_word_plan(self.copy,self.analysis,self.spec,fields)
                self.events.put((self,'pdf',(revision,pdf.read_bytes())))
        except Exception as exc:
            self.events.put((self,'error',str(exc)))
        finally:
            if process:
                process.stdin.close()
                process.wait()
            shutil.rmtree(self.preview_dir,ignore_errors=True)


class Workspace:
    def __init__(self, root):
        self.root=root
        root.title('Бюро ИД · Документы проекта');root.geometry('1380x820');root.minsize(800,480)
        root.configure(bg=BG)
        self.events=queue.Queue();self.sessions={};self.current=None;self.models={}
        self.pending={};self.revisions={};self.latest={};self.manual=set()
        self.windows={};self.holders={};self.body={};self.views={};self.zoom=70;self.collapsed=set();self.panel_contents={};self.collapsed_dirty=set()
        self.paths=sorted(p for p in SAMPLES.glob('*/*.xlsx') if p.name.startswith('АОСР'))[:2]
        self.style=ttk.Style();self.style.theme_use('clam')
        self.style.configure('Treeview',font=('Segoe UI',9),rowheight=23,background=PAPER)
        self.header=tk.Frame(root,bg='#3e3430');self.header.pack(fill='x')
        tk.Label(self.header,text='Бюро ИД   /   Рабочая область',bg='#3e3430',fg='white',font=('Segoe UI',14)).pack(side='left',padx=16,pady=10)
        ttk.Button(self.header,text='Открыть документ…',command=self.choose).pack(side='right',padx=12)
        self.status=tk.StringVar(value='Загрузка проекта')
        ttk.Label(root,textvariable=self.status,padding=6).pack(side='bottom',fill='x')
        self.split=tk.PanedWindow(root,orient='horizontal',bg='#ddcfc6',sashwidth=6,showhandle=False)
        self.split.pack(fill='both',expand=True)
        for n,width in enumerate((240,465,540)):
            h=tk.Frame(self.split,bg=BG);self.holders[n]=h;self.split.add(h,width=width,minsize=120,stretch='always')
            self.build(n)
        self._poll_job=self.root.after(80,self.poll)
        def cancel_poll(event):
            if event.widget is root and self._poll_job is not None:
                try:root.after_cancel(self._poll_job)
                except tk.TclError:pass
                self._poll_job=None
        root.bind('<Destroy>',cancel_poll,add='+')
        if self.paths:self.open(self.paths[0])
        root.protocol('WM_DELETE_WINDOW',self.close)
        self.hidden_windows={}
        root.bind('<Unmap>',self.hide_floaters,add='+')
        root.bind('<Map>',self.show_floaters,add='+')

    def build(self,n):
        if n==1:self.release_form_variables()
        if n in getattr(self,'collapsed',set()):self.collapsed_dirty.add(n);return
        host=self.windows.get(n,self.holders[n])
        for child in host.winfo_children():child.destroy()
        self.pane_header(n,host)
        b=tk.Frame(host,bg=PAPER);b.pack(fill='both',expand=True);self.body[n]=b
        if n==0:self.tree()
        elif n==1:self.form()
        else:self.preview()

    def pane_header(self,n,host):
        bar=tk.Frame(host,bg=ACCENT);bar.panel_header=True;bar.pack(fill='x')
        tk.Label(bar,text=NAMES[n],bg=ACCENT,font=('Segoe UI',10,'bold')).pack(side='left',padx=6,pady=6)
        def button(label,action):
            ttk.Button(bar,text=label,command=action,style='Window.TButton',width=0 if label=='Вернуть' else 2,takefocus=False).pack(side='right')
        if n in self.windows:
            button('Вернуть',lambda:self.dock(n));button('—',lambda:self.collapse_panel(n))
            button('□',lambda:self.maximize(self.windows[n]))
        else:
            button('↗',lambda:self.detach(n));button('□',lambda:self.detach(n,True))
            button('—',lambda:self.collapse_panel(n))

    def panel_placeholder(self,n,host=None,action=None):
        host=host or self.holders[n]
        for child in host.winfo_children():child.destroy()
        button=ttk.Button(host,text='Вернуть · '+NAMES[n],style='Compact.TButton',command=action or (lambda:self.restore_panel(n)))
        button.pack(padx=10,pady=12,anchor='n')
        if hasattr(self,'paint'):self.paint(host)
    def collapse_panel(self,n):
        if n in self.windows:
            self.windows[n].withdraw();self.panel_placeholder(n,action=lambda:self.restore_panel(n));return
        if n in self.collapsed:return
        self.collapsed.add(n)
        host=self.holders[n];contents=[]
        for child in host.pack_slaves():
            contents.append((child,child.pack_info()));child.pack_forget()
        button=ttk.Button(host,text='Вернуть · '+NAMES[n],style='Compact.TButton',command=lambda:self.restore_panel(n));button.pack(padx=10,pady=12,anchor='n')
        self.panel_contents[n]=(contents,button)
        if hasattr(self,'paint'):self.paint(host)
    def release_form_variables(self):
        # Dispose traces in the UI thread before rebuilding fields. Otherwise
        # background Python GC can enter Tcl from an Office/renderer thread.
        old=getattr(self,'views',{});self.views={}
        for variable in old.values():
            if isinstance(variable,tk.Variable):
                try:
                    owned=set(variable._tclCommands or ())
                    for mode,callback in variable.trace_info():
                        if callback in owned:variable.trace_remove(mode,callback)
                except tk.TclError:pass
    def restore_panel(self,n):
        if n in self.windows:
            self.windows[n].deiconify();self.windows[n].lift()
            self.panel_placeholder(n,action=lambda:self.dock(n))
        else:
            self.collapsed.discard(n)
            saved=self.panel_contents.pop(n,None)
            if saved and n not in self.collapsed_dirty:
                contents,button=saved;button.destroy()
                for child,options in contents:
                    if child.winfo_exists():child.pack(**options)
                if n==2:self.draw()
            else:
                self.collapsed_dirty.discard(n);self.build(n)
        if hasattr(self,'enforce_panel_sizes'):self.root.after_idle(self.enforce_panel_sizes)

    def hide_floaters(self,event):
        if event.widget is self.root and self.root.state()=='iconic':
            for n,w in self.windows.items():
                if w.state() in ('normal','zoomed'):
                    self.hidden_windows[n]=w.state()
                    w.withdraw()

    def show_floaters(self,event):
        if event.widget is self.root and self.root.state() in ('normal','zoomed'):
            for n,state in list(self.hidden_windows.items()):
                if n in self.windows:
                    self.windows[n].deiconify()
                    self.windows[n].state(state)
            self.hidden_windows.clear()

    def maximize(self,w):
        from ui_surface import transition
        from windows_integration import monitor_bounds,cover_monitor
        from taskbar_reveal import install
        install(w)
        active=bool(w.attributes('-fullscreen'))
        if active and getattr(w,'_maximize_from_dock',False):
            n=next((n for n,win in self.windows.items() if win is w),None)
            if n is not None:self.dock(n);return
        def apply():
            if active:
                w.taskbar_reveal['reset']();w.attributes('-fullscreen',False)
                w.state('normal')
                if getattr(w,'app_caption',None):w.app_caption.reconcile()
                w.geometry(w._before_panel_full)
                from ui_surface import restore_client_size
                w.after_idle(lambda:restore_client_size(w,w._before_panel_full))
                w._bottom_safe.pack_forget()
            else:
                if w is not self.root and getattr(self.root,'taskbar_reveal',None):self.root.taskbar_reveal['reset']()
                w._before_panel_full=w.geometry();w.state('normal')
                if not hasattr(w,'_bottom_safe'):
                    w._bottom_safe=tk.Frame(w,height=26,bg=self.colors['bg']);w._bottom_safe.tone='bg'
                w._bottom_safe.pack(side='bottom',fill='x',before=w.winfo_children()[0])
                w.attributes('-fullscreen',True);bounds=monitor_bounds(w)
                w.after_idle(lambda:cover_monitor(w,bounds) if w.winfo_exists() else None)
        transition(w,apply)

    def detach(self,n,maximized=False):
        self.collapsed.discard(n)
        self.panel_contents.pop(n,None);self.collapsed_dirty.discard(n)
        win=tk.Toplevel(self.root);win.title(NAMES[n]+' · Бюро ИД');win.geometry('760x650')
        self.windows[n]=win
        from windows_integration import normal_window
        normal_window(win)
        host=self.holders[n]
        for child in host.winfo_children():child.destroy()
        ttk.Button(host,text='Вернуть · '+NAMES[n],command=lambda:self.dock(n)).pack(pady=12)
        win.protocol('WM_DELETE_WINDOW',lambda:self.dock(n))
        if hasattr(self,'escape_full'):win.bind('<Escape>',self.escape_full,add='+')
        self.build(n)
        if maximized:
            win._maximize_from_dock=True;self.maximize(win)

    def dock(self,n):
        self.collapsed.discard(n)
        self.panel_contents.pop(n,None);self.collapsed_dirty.discard(n)
        win=self.windows.pop(n,None)
        if win:win.destroy()
        self.build(n)

    def tree(self):
        c=self.body[0]
        tk.Label(c,text='▾  Проект',bg=PAPER,font=('Segoe UI',10,'bold')).pack(anchor='w',padx=8,pady=8)
        groups={}
        for p in self.paths:groups.setdefault(p.parent.parent.name,[]).append(p)
        for section,items in groups.items():
            tk.Label(c,text='  └─ '+section,bg=PAPER,font=('Segoe UI',9)).pack(anchor='w')
            for j,p in enumerate(items):
                tk.Button(c,text=('     └─ ' if j==len(items)-1 else '     ├─ ')+p.stem,anchor='w',
                          wraplength=210,font=('Segoe UI',8),bg=ACCENT if self.current and p==self.current.source else PAPER,
                          bd=0,command=lambda p=p:self.open(p)).pack(fill='x')

    def choose(self):
        name=filedialog.askopenfilename(filetypes=[('Word и Excel','*.xlsx *.xls *.docx *.doc')])
        if name:self.open(Path(name))

    def open(self,path):
        try:
            if path not in self.paths:self.paths.append(path)
            if path not in self.sessions:self.sessions[path]=Session(path,self.events)
            self.current=self.sessions[path]
            self.revisions.setdefault(self.current,0)
            for n in range(3):self.build(n)
            self.status.set('Рабочая копия · '+str(self.current.copy))
        except Exception as exc:messagebox.showerror('Бюро ИД',str(exc))

    def form(self):
        b=self.body[1];s=self.current;self.views={}
        if not s:return
        ttk.Label(b,text=s.source.stem,wraplength=370,font=('Segoe UI',12,'bold'),padding=8).pack(anchor='w')
        if s not in self.models:
            ttk.Label(b,text='Открываем документ…').pack();return
        vals=self.models[s]
        if not vals:
            ttk.Label(b,text='Для этого шаблона ещё не назначены поля.',padding=10).pack();return
        canvas=tk.Canvas(b,bg=PAPER,highlightthickness=0);self.form_canvas=canvas;scroll=Scrollbar(b,command=canvas.yview)
        from ui_surface import install_repaint
        repaint=install_repaint(canvas)
        canvas.configure(yscrollcommand=lambda a,z:(scroll.set(a,z),repaint()));scroll.pack(side='right',fill='y');canvas.pack(fill='both',expand=True)
        inner=tk.Frame(canvas,bg=PAPER);item=canvas.create_window(0,0,window=inner,anchor='nw')
        inner.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
        for key,text in (self.visible_fields(s,vals,b) if hasattr(self,"visible_fields") else vals).items():
            tk.Label(inner,text=getattr(s,'labels',{}).get(key,LABELS.get(key,key)),bg=PAPER,anchor='w').pack(fill='x',padx=12,pady=(6,1))
            if key in DATES:
                var=tk.StringVar(value=self.human(text));e=ttk.Entry(inner,textvariable=var)
                self.views[key]=var
                var.trace_add('write',lambda *a,k=key,v=var:self.edit_date(s,k,v.get()))
            else:
                var=tk.StringVar(value=text)
                history=[]
                e=ttk.Combobox(inner,textvariable=var,values=history)
                self.views[key]=var
                var.trace_add('write',lambda *a,k=key,v=var:self.changed(s,k,v.get()))
            e.pack(fill='x',padx=12,ipady=3)
        ttk.Label(inner,text='Даты вводятся как ДД.ММ.ГГГГ. В документе применяется формат шаблона.',wraplength=300,padding=10).pack(anchor='w')

    @staticmethod
    def human(iso):
        return datetime.strptime(iso,'%Y-%m-%d').strftime('%d.%m.%Y') if iso else ''

    def edit_date(self,s,key,v):
        try:iso=datetime.strptime(v,'%d.%m.%Y').date().isoformat() if v else ''
        except ValueError:
            self.status.set('Введите полную дату ДД.ММ.ГГГГ');return
        if getattr(self,'following',False):return
        if key=='date':self.manual.add(s)
        self.changed(s,key,iso)
        if key=='end' and s not in self.manual:
            self.models[s]['date']=iso;self.following=True
            try:self.views['date'].set(v)
            finally:self.following=False

    def changed(self,s,key,v):
        if self.models[s].get(key)==v:return
        entry=getattr(s,'spec',{}).get(key,{})
        try:
            if v and entry.get('kind')=='datecell':datetime.strptime(v,'%d.%m.%Y')
            if v and entry.get('kind')=='number' and (not v.isdigit() or int(v)<1):raise ValueError()
        except ValueError:
            self.status.set('Проверьте дату или количество листов.');return
        self.models[s][key]=v;self.revisions[s]+=1
        if s in self.pending:self.root.after_cancel(self.pending.pop(s))
        self.status.set('Изменения приняты · готовим PDF')
        self.pending[s]=self.root.after(400,lambda:self.submit(s))

    def submit(self,s):
        self.pending.pop(s,None);s.tasks.put((dict(self.models[s]),self.revisions[s]))

    def preview(self):
        if getattr(self,'reference_path',None):
            from pdf_page_preview import PagePreview
            self.reference_label=ttk.Label(self.body[2],text=self.reference_path.name,wraplength=400,padding=6);self.reference_label.pack(fill='x')
            view=PagePreview(self.body[2],self);view.zoom=getattr(self,'reference_zoom',self.zoom);view.scale.set(view.zoom);view.on_zoom=lambda z:setattr(self,'reference_zoom',z);self.reference_view=view;view.pack(fill='both',expand=True);self.preview_selection=view.selection;view.show(self.reference_path,0);return
        from pdf_page_preview import PagePreview
        view=PagePreview(self.body[2],self);view.zoom=self.zoom;view.scale.set(self.zoom)
        view.pack(fill='both',expand=True);self.pdf_viewer=view;self.canvas=view.canvas;self.preview_selection=view.selection
        view.canvas.bind('<FocusIn>',lambda e:setattr(self,'active_panel',2),add='+')
        view.on_zoom=lambda z:setattr(self,'zoom',z)
        self.draw()

    def rescale(self,z):
        self.zoom=z;self.pdf_viewer.set_zoom(z)

    def draw(self):
        if 2 in getattr(self,'collapsed',set()):return
        if getattr(self,'reference_path',None):return
        data=self.latest.get(self.current)
        if not data:return
        review=getattr(self.current,'review_pdf',None)
        if review and review[0]==self.saved_rev.get(self.current):data=review[1]
        view=self.pdf_viewer;had_pages=bool(view.pages)
        if getattr(view,'document_identity',None) is not self.current:view.clear_draft()
        draft=view.field_draft
        if draft and self.saved_rev.get(self.current)==self.revisions.get(self.current) and self.models.get(self.current,{}).get(draft[0])==draft[1]:view.clear_draft()
        snapshot=getattr(self.current,'verified_values',None)
        view.set_quick_model(snapshot[1] if snapshot and snapshot[0]==self.saved_rev.get(self.current) else {},getattr(self.current,'labels',{}))
        page=view.page_at(view.canvas.canvasy(0)) if had_pages else 0
        fraction=(view.canvas.canvasy(0)-view.pages[page][0])/view.pages[page][2] if had_pages else 0
        identity=self.current
        retain=getattr(view,'document_identity',None) is identity
        view.document_identity=identity;view.guides=getattr(self.current,'guides',{})
        view.guides_enabled=any(k.startswith('row') for k in self.models.get(self.current,{}))
        view.show(data,page,retain=retain)
        if had_pages and view._sizes is None:
            view._restore_fraction=(view._generation,page,fraction)
        elif had_pages and view.pages:
            page=min(page,len(view.pages)-1);y=view.pages[page][0]+fraction*view.pages[page][2]
            view.canvas.yview_moveto(y/view.height)
        elif had_pages:
            view._restore_fraction=(view._generation,page,fraction)

    def poll(self):
        while not self.events.empty():
            s,kind,payload=self.events.get()
            if self.sessions.get(s.source) is not s:continue
            if kind in ('rows','error') and getattr(self,'row_wait',None):
                self.row_wait.destroy();self.row_wait=None
            if kind=='notice':messagebox.showinfo('Реестр',payload,parent=self.root)
            elif kind=='fields':
                self.models[s]=payload
                if getattr(s,'register_repaired',False) and hasattr(self,'mark_changed'):
                    self.mark_changed(s)
                if hasattr(self,'journal') and self.project:
                    j=self.journal();draft=j.drafts.get(str(s.source.relative_to(j.base)))
                    if draft:
                        self.models[s].update({k:v for k,v in draft.items() if k in payload});self.revisions[s]+=1
                        self.pending[s]=self.root.after(400,lambda session=s:self.submit(session))
                if s==self.current:self.build(1)
            elif kind=='rows':
                fields,row=payload;self.models[s]=fields;self.row_choice[s]=row;s.row_operation_busy=False
                if hasattr(self,'journal') and self.project:
                    j=self.journal();j.drafts[str(s.source.relative_to(j.base))]=dict(fields)
                    from recovery_state import persist
                    persist(j)
                self.history.pop(s,None);self.redo.pop(s,None)
                if getattr(s,'row_operations',[]) and hasattr(self,'start_register_operation'):self.start_register_operation(s)
                elif s==self.current:self.build(1)
            elif kind in ('clean','pdf'):
                rev,data=payload
                if rev==self.revisions.get(s,0):
                    unchanged=kind=='clean' and self.latest.get(s)==data
                    self.latest[s]=data
                    if hasattr(self,'saved_rev'):self.saved_rev[s]=rev
                    if s==self.current and not unchanged:self.draw();self.status.set('PDF обновлён · '+str(s.source))
            elif kind=='error':
                s.row_operation_busy=False
                if hasattr(s,'row_operations'):s.row_operations.clear()
                if s==self.current:self.build(1)
                self.status.set(payload);messagebox.showerror('Предпросмотр',payload)
        if self.root.winfo_exists():self._poll_job=self.root.after(100,self.poll)

    def close(self):
        for s in list(self.pending):
            self.root.after_cancel(self.pending[s]);self.submit(s)
        for s in self.sessions.values():s.tasks.put(None)
        self.root.withdraw()
        def finish():
            if any(s.thread.is_alive() for s in self.sessions.values()):self.root.after(150,finish)
            else:self.root.destroy()
        finish()


if __name__=='__main__':
    from studio import Studio
    root=tk.Tk()
    root.withdraw()
    app=Studio(root)
    root.deiconify()
    root.mainloop()






