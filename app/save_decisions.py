"""A reversible editing session and an explicit save decision before leaving it."""
from pathlib import Path
import tempfile
import shutil
import json
import tkinter as tk
from tkinter import ttk,messagebox

class ProjectJournal:
    def __init__(self,project):
        self.project=project
        self.base=project/'Документы'
        from recovery_state import PersistentSpace
        self.temp=PersistentSpace(project/'.recovery')
        self.root=Path(self.temp.name)
        self.files={p.relative_to(self.base) for p in self.base.rglob('*') if p.is_file() and not p.name.startswith('~$')}
        self.dirs={p.relative_to(self.base) for p in self.base.rglob('*') if p.is_dir()}
        self.manifest=(project/'project.json').read_bytes()
        self.copies={};self.dirty=set();self.removed=set()
        self.origins={};self.checkpoints={};self.changed=set();self.working={};self.saved_names={}
        from recovery_state import load
        load(self)
    def protect(self,path):
        rel=path.relative_to(self.base)
        rel=self.origins.get(rel,rel)
        if rel in self.files and rel not in self.copies and path.is_file():
            dest=self.root/'baseline'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest);self.copies[rel]=dest
            from recovery_state import persist
            persist(self)
    def work_file(self,path):
        import uuid
        rel=path.relative_to(self.base)
        if rel not in self.working:
            self.working[rel]=self.root/'working'/uuid.uuid4().hex/path.name
            from recovery_state import persist
            persist(self)
        return self.working[rel]
    def move_paths(self,source,target):
        """Remap live identity, keeping the opening baseline immutable."""
        old=source.relative_to(self.base);new=target.relative_to(self.base)
        def move(rel):return new/rel.relative_to(old) if rel==old or rel.is_relative_to(old) else rel
        candidates=set(self.files)|set(self.origins)|set(self.working)
        origins=dict(self.origins)
        for rel in candidates:
            if rel==old or rel.is_relative_to(old):
                origins[move(rel)]=self.origins.get(rel,rel)
                origins.pop(rel,None)
        self.origins=origins
        for name in ('working','checkpoints','saved_names'):
            setattr(self,name,{move(k):v for k,v in getattr(self,name).items()})
        self.drafts={str(move(Path(k))):v for k,v in self.drafts.items()}
        self.dirty={self.base/move(p.relative_to(self.base)) for p in self.dirty}
        self.changed={self.base/move(p.relative_to(self.base)) for p in self.changed}
        from recovery_state import persist
        persist(self)
    def restore_document(self,path):
        rel=path.relative_to(self.base)
        origin=self.origins.get(rel,rel)
        target=self.base/self.saved_names.get(rel,origin)
        if target!=path and target.exists():raise ValueError('Не удалось вернуть имя: '+target.name+' уже существует.')
        baseline=self.checkpoints.get(rel) or self.copies.get(origin)
        had_checkpoint=rel in self.checkpoints
        work=self.working.pop(rel,None)
        if work:work.unlink(missing_ok=True)
        self.dirty.discard(path);self.drafts.pop(str(rel),None)
        old_key=str(path.relative_to(self.project))
        if target!=path:
            target.parent.mkdir(parents=True,exist_ok=True);path.rename(target)
            self.move_paths(path,target);self.removed.discard(target)
            path=target;rel=path.relative_to(self.base)
        if baseline:
            path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline,path)
        elif origin not in self.files:path.unlink(missing_ok=True)
        self.dirty.discard(path)
        self.drafts.pop(str(rel),None)
        from recovery_state import persist
        persist(self)
        data=json.loads((self.project/'project.json').read_text('utf-8'))
        original=json.loads(self.manifest)
        key=str(path.relative_to(self.project))
        edited=set(data.get('edited',[]));edited.discard(key);edited.discard(old_key)
        if key in original.get('edited',[]) or had_checkpoint:edited.add(key)
        data['edited']=sorted(edited)
        (self.project/'project.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf-8')
        return path
    def commit_document(self,path):
        rel=path.relative_to(self.base)
        if path.exists():
            dest=self.root/'checkpoints'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest);self.checkpoints[rel]=dest
        self.dirty.discard(path)
        self.changed.add(path)
        self.saved_names[rel]=rel
        self.drafts.pop(str(rel),None)
        from recovery_state import persist
        persist(self)
    def publish_working(self,path):
        work=self.working.get(path.relative_to(self.base))
        if not work or work==path:return
        if not path.exists():return # explicitly removed from the project
        self.protect(path)
        temp=path.with_name(path.name+'.bureau-saving')
        shutil.copy2(work,temp);temp.replace(path)
    def restore(self):
        for p in self.base.rglob('*'):
            if p.is_file() and not p.name.startswith('~$') and p.relative_to(self.base) not in self.files:p.unlink()
        for rel in self.dirs:(self.base/rel).mkdir(parents=True,exist_ok=True)
        for rel,source in self.copies.items():
            path=self.base/rel;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,path)
        for p in sorted(self.base.rglob('*'),key=lambda p:len(p.parts),reverse=True):
            if p.is_dir() and p.relative_to(self.base) not in self.dirs and not any(p.iterdir()):p.rmdir()
        (self.project/'project.json').write_bytes(self.manifest)
        self.dirty.clear()
        self.changed.clear()
        self.removed.clear()
    def dirty_project(self):
        existing={p.relative_to(self.base) for p in self.base.rglob('*') if p.is_file() and not p.name.startswith('~$')}
        return bool(self.dirty or self.changed or self.removed or existing!=self.files or {p.relative_to(self.base) for p in self.base.rglob('*') if p.is_dir()}!=self.dirs)

class SaveDecisions:
    def journal(self):
        if not self.project:return None
        if self.project not in self.journals:self.journals[self.project]=ProjectJournal(self.project)
        return self.journals[self.project]
    def needs_project_decision(self):
        j=self.journal()
        return j and j.dirty_project()
    def ask_save(self,title,callback):
        if getattr(self,'decision',None) and self.decision.winfo_exists():
            self.decision.focus_set();return
        win=tk.Toplevel(self.root);self.decision=win
        win.transient(self.root)
        win.title('Сохранение изменений');win.geometry('480x155');win.resizable(False,False)
        ttk.Label(win,text=title,wraplength=465,padding=16).pack(fill='x')
        row=ttk.Frame(win);row.pack(side='bottom',fill='x',padx=12,pady=10)
        buttons=ttk.Frame(row);buttons.pack(side='right')
        def choose(result):
            win.grab_release();win.destroy();self.decision=None
            callback(result)
        for text,result,icon in [('Сохранить','save','save'),('Не сохранять','discard','close'),('Вернуться','cancel','undo')]:
            button=ttk.Button(buttons,text=text,image=self.icon(icon),compound='left',style='Compact.TButton',command=lambda r=result:choose(r))
            button.pack(side='left',padx=3)
        win.protocol('WM_DELETE_WINDOW',lambda:choose('cancel'))
        self.paint(win);win.grab_set();win.focus_set()
    def stop_sessions(self,sessions,done,require_saved=False):
        sessions=list(sessions)
        if any(getattr(s,'row_operation_busy',False) or getattr(s,'row_operations',[]) for s in sessions):
            self.stopping=True;self.root.after(80,lambda:self.stop_sessions(sessions,done,require_saved));return
        wait=tk.Toplevel(self.root);wait.title('Документы');self.stopping=True
        ttk.Label(wait,text='Завершаем операции с документами…',padding=18).pack()
        wait.protocol('WM_DELETE_WINDOW',lambda:None);self.paint(wait);wait.grab_set()
        def finish():
            if any(s.thread.is_alive() for s in sessions):self.root.after(100,finish);return
            wait.grab_release();wait.destroy();self.stopping=False
            failed=[s for s in sessions if s in self.revisions and (self.saved_rev.get(s,-1)<self.revisions[s] or s.validated_revision<self.revisions[s] or s.formula_errors)]
            if require_saved and failed:
                messagebox.showerror('Сохранение','Не все изменения записаны. Проверьте документ или выберите «Не сохранять».')
                return
            for s in sessions:
                s.closed_pdf=(self.latest.get(s),self.revisions.get(s))
                self.sessions.pop(s.source,None)
                for store in (self.models,self.latest,self.revisions,self.saved_rev,self.history,self.redo):store.pop(s,None)
            done()
        def begin_close():
            for s in sessions:
                if s in getattr(self,'pending',{}):
                    self.root.after_cancel(self.pending[s]);self.submit(s)
            if require_saved:
                pending=[s for s in sessions if s in self.revisions and (self.saved_rev.get(s,-1)<self.revisions[s] or s.validated_revision<self.revisions[s])]
                broken=[s for s in pending if not s.thread.is_alive()]
                errors=[s for s in sessions if s in self.revisions and s.validated_revision==self.revisions[s] and s.formula_errors]
                if broken or errors:
                    wait.grab_release();wait.destroy();self.stopping=False
                    messagebox.showerror('Проверка документа','Не удалось подтвердить сохранение. Исправьте ошибки формул/документа или выберите «Не сохранять». Рабочая копия сохранена.');return
                if pending:self.root.after(60,begin_close);return
            for s in sessions:s.tasks.put(None)
            finish()
        begin_close()
    def decide_document(self,s,done):
        j=self.journal()
        rel=s.source.relative_to(j.base) if j else None
        renamed=j and j.saved_names.get(rel,j.origins.get(rel,rel))!=rel
        if not j or s.source not in j.dirty and not renamed:
            done();return
        def result(choice):
            if choice=='cancel':return
            def complete():
                if choice=='discard':
                    try:
                        restored=j.restore_document(s.source)
                        if restored!=s.source:
                            self.update_path_links(s.source,restored);s.source=restored
                            self.selected[0]=str(restored)
                            from studio import docs
                            self.paths=docs(self.project/'Документы')
                    except (OSError,ValueError) as e:messagebox.showerror('Отмена изменений',str(e));return
                else:j.commit_document(s.source)
                done()
            if choice=='save':self.save_session(s,lambda:(j.commit_document(s.source),done()))
            else:self.stop_sessions([s],complete)
        self.ask_save('Сохранить изменения в документе «'+s.source.name+'»?',result)
    def save_session(self,s,done):
        """Wait asynchronously for the working copy; never restart Office to save."""
        if s in self.pending:self.root.after_cancel(self.pending[s]);self.submit(s)
        wait=tk.Toplevel(self.root);wait.title('Сохранение');wait.transient(self.root)
        ttk.Label(wait,text='Сохраняем документ…',padding=18).pack();self.paint(wait);wait.grab_set()
        wait.protocol('WM_DELETE_WINDOW',lambda:None);self.stopping=True
        def release():
            wait.grab_release();wait.destroy();self.stopping=False
        def finish():
            if not s.thread.is_alive():
                release()
                messagebox.showerror('Сохранение','Редактор документа завершился. Изменения оставлены в восстановлении.');return
            if self.saved_rev.get(s,-1)!=self.revisions.get(s) or s.validated_revision<self.revisions.get(s,0) or getattr(s,'row_operation_busy',False) or getattr(s,'row_operations',[]):
                self.root.after(60,finish);return
            if s.formula_errors:
                release();messagebox.showerror('Проверка формул','В документе найдены ошибки формул: '+', '.join(s.formula_errors)+'. Исходный файл не заменён.');return
            try:
                self.journal().publish_working(s.source)
            except OSError as e:release();messagebox.showerror('Сохранение',str(e));return
            release()
            self.cache_final_pdf(s)
            done()
        finish()
    def cache_final_pdf(self,s):
        data,revision=getattr(s,'closed_pdf',(self.latest.get(s),self.revisions.get(s)))
        if not data or s.validated_revision!=revision or s.formula_errors:return
        from final_pdf_cache import FinalPDFCache
        import threading
        threading.Thread(target=FinalPDFCache().put,args=(s.source,data,s.clean_hash),daemon=True).start()
    def decide_project(self,done):
        j=self.journal()
        sessions=[s for s in [*self.sessions.values(),*getattr(self,'retiring_sessions',[])] if self.project and s.source.is_relative_to(self.project)]
        def finish(choice):
            if choice=='cancel':return
            def complete():
                self.cancel_scan()
                try:
                    if choice=='save':
                        from recovery_state import archive
                        archive(j)
                        for path in list(j.dirty):j.publish_working(path)
                        for s in sessions:self.cache_final_pdf(s)
                    if choice=='discard':j.restore()
                except OSError as e:
                    messagebox.showerror('Сохранение проекта','Не удалось завершить операцию. Рабочие копии сохранены для повторной попытки.\n'+str(e));return
                if j:
                    self.journals.pop(j.project,None);j.temp.cleanup()
                self.current=None;done()
            if sessions:self.stop_sessions(sessions,complete,choice=='save')
            else:complete()
        if j and j.dirty_project():self.ask_save('Сохранить изменения проекта «'+self.project.name+'»?',finish)
        else:finish('save')
    def close_document(self):
        s=self.current
        if not s:return
        def done():
            self.current=None
            for n in (0,1,2):self.build(n)
        self.decide_document(s,done)
    def delete_document(self):
        selected=self.selected.get(0,'')
        path=Path(selected) if selected else self.current.source if self.current else None
        if not path or not path.is_file():return
        if not messagebox.askyesno('Удаление','Удалить из текущего проекта «'+path.name+'»?'):return
        j=self.journal();j.protect(path)
        def remove():
            path.unlink();j.removed.add(path)
            self.paths=[p for p in self.paths if p!=path]
            if self.current and self.current.source==path:self.current=None
            for n in (0,1,2):self.build(n)
        session=self.sessions.get(path)
        if session:self.stop_sessions([session],remove)
        else:remove()
    def close(self):
        if getattr(self,'stopping',False):return
        if getattr(self,'decision',None) and self.decision.winfo_exists():self.decision.focus_set();return
        def quit():
            self.cancel_scan()
            for j in self.journals.values():j.temp.cleanup()
            self.journals.clear();self.root.destroy()
        if self.project:self.decide_project(quit)
        else:quit()
