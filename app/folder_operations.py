"""Filesystem operations within a project, covered by its reversible edit journal."""
from pathlib import Path
import json,shutil
import tkinter as tk
from tkinter import ttk,simpledialog,messagebox

class FolderOperations:
    def project_path(self,path,allow_root=False):
        raw=Path(path)
        if raw.is_symlink() or (hasattr(raw,'is_junction') and raw.is_junction()):
            raise ValueError('Ссылочные папки не поддерживаются.')
        base=(self.project/'Документы').resolve();path=raw.resolve()
        if not path.is_relative_to(base) or (path==base and not allow_root):raise ValueError('Выберите файл или папку внутри документов проекта.')
        if path.is_symlink() or (hasattr(path,'is_junction') and path.is_junction()):raise ValueError('Ссылочные папки не поддерживаются.')
        return path
    def selected_document_path(self):
        text=self.selected.get(0,'')
        return Path(text) if text else self.current.source if self.current else self.project/'Документы'
    def selected_directory(self):
        path=self.project_path(self.selected_document_path(),True)
        return path if path.is_dir() else path.parent
    def folder_name(self,initial='Новая папка'):
        from app_dialogs import ask_text
        value=ask_text(self,'Название','Введите название',initial)
        if value is None:return None
        value=value.strip()
        if not value or value in ('.','..') or any(c in value for c in '<>:"/\\|?*') or value.endswith('.'):
            messagebox.showerror('Название','Недопустимое название.');return None
        return value
    def new_folder(self):
        if not self.project:return
        try:
            parent=self.selected_directory();name=self.folder_name()
            if name is None:return
            target=parent/name;target.mkdir()
            self.expanded[0].add(str(parent.resolve()));self.expanded[0].add(str(target.resolve()));self.refresh_documents()
        except (OSError,ValueError) as e:messagebox.showerror('Создание папки',str(e))
    def refresh_documents(self):
        from studio import docs
        self.paths=docs(self.project/'Документы')
        for n in (0,3):self.build(n)
    def protect_folder(self,path):
        journal=self.journal()
        for file in ([path] if path.is_file() else path.rglob('*')):
            if file.is_file():
                self.project_path(file);journal.protect(file)
    def update_path_links(self,source,target=None):
        base=self.project/'Документы';file=self.project/'project.json';data=json.loads(file.read_text('utf-8'))
        def move(value,relative):
            old=relative/value
            if old==source or old.is_relative_to(source):
                return str((target/old.relative_to(source)).relative_to(relative)) if target else None
            return value
        data['edited']=[v for v in (move(v,self.project) for v in data.get('edited',[])) if v is not None]
        links=[]
        for record in data.get('package_links',[]):
            record={**record,'file':move(record['file'],base),'act':move(record['act'],base)}
            if record['file'] is not None and record['act'] is not None:links.append(record)
        data['package_links']=links
        tmp=file.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf-8');tmp.replace(file)
    def perform_file_operation(self,source,operation,target=None):
        try:
            source=self.project_path(source)
            if target is not None:
                target=self.project_path(target,True)
                if target.exists():raise ValueError('Файл или папка с таким названием уже существует.')
                if target.is_relative_to(source):raise ValueError('Нельзя переместить папку внутрь неё самой.')
            self.protect_folder(source)
        except (OSError,ValueError) as e:messagebox.showerror('Документы',str(e));return
        affected=[s for s in self.sessions.values() if s.source==source or s.source.is_relative_to(source)]
        old_current=self.current.source if self.current and self.current in affected else None
        def apply():
            try:
                if operation=='copy':
                    if source.is_dir():shutil.copytree(source,target)
                    else:shutil.copy2(source,target)
                elif operation=='move':
                    source.rename(target);self.update_path_links(source,target)
                    self.journal().removed.add(source)
                    self.journal().move_paths(source,target)
                    for s in affected:
                        self.sessions.pop(s.source,None)
                        s.source=target/s.source.relative_to(source);self.sessions[s.source]=s
                        self.journal().dirty.add(s.source)
                    from recovery_state import persist
                    persist(self.journal())
                else:
                    if source.is_dir():shutil.rmtree(source)
                    else:source.unlink()
                    self.update_path_links(source);self.journal().removed.add(source)
                if old_current and operation=='delete':self.current=None
                self.selected[0]=str(target or source.parent);self.expanded[0].add(str((target or source.parent).parent.resolve()))
                self.refresh_documents()
                for n in (1,2):self.build(n)
            except (OSError,ValueError) as e:messagebox.showerror('Документы',str(e))
        if affected and operation=='delete':self.stop_sessions(affected,apply)
        else:apply()
    def rename_document(self):
        source=self.selected_document_path();name=self.folder_name(source.name)
        if name:self.perform_file_operation(source,'move',source.with_name(name))
    def delete_document(self):
        source=self.selected_document_path()
        if not source.exists():return
        if messagebox.askyesno('Удаление','Удалить из проекта «'+source.name+'»?',parent=self.root):
            self.perform_file_operation(source,'delete')
    def file_clipboard(self,cut=False):
        try:self.path_clipboard=(self.project_path(self.selected_document_path()),cut)
        except ValueError as e:messagebox.showinfo('Документы',str(e))
    def paste_document(self):
        value=getattr(self,'path_clipboard',None)
        if not value:return
        source,cut=value
        if not source.exists():messagebox.showinfo('Вставка','Исходный файл или папка отсутствует.');return
        from studio import next_path
        try:
            parent=self.selected_directory()
            if parent==source or parent.is_relative_to(source):raise ValueError('Выберите другую папку для вставки.')
            dest=next_path(parent/source.name)
            self.perform_file_operation(source,'move' if cut else 'copy',dest)
            if cut:self.path_clipboard=None
        except ValueError as e:messagebox.showerror('Вставка',str(e))
    def document_context(self,tree,event):
        node=tree.identify_row(event.y)
        if node:tree.selection_set(node);tree.focus(node);self.selected[0]=self.tree_selection(tree)
        menu=tk.Menu(tree,tearoff=False)
        c=self.colors;menu.configure(bg=c['paper'],fg=c['text'],activebackground=c['hover'],activeforeground='#111111')
        actions=[('Создать папку',self.new_folder),('Переименовать',self.rename_document),
                 ('Вырезать',lambda:self.file_clipboard(True)),('Копировать',self.file_clipboard),
                 ('Вставить',self.paste_document),('Удалить из проекта',self.delete_document)]
        for text,fn in actions:menu.add_command(label=text,command=fn)
        try:menu.tk_popup(event.x_root,event.y_root)
        finally:menu.grab_release()
    def folder_drag(self,tree):
        state=[None]
        def press(event):
            node=tree.identify_row(event.y)
            if node:
                value=tree.item(node,'values')
                state[0]=(Path(value[0]),event.x_root,event.y_root) if value else None
        def release(event):
            if not state[0]:return
            source,x,y=state[0];state[0]=None
            if abs(event.x_root-x)+abs(event.y_root-y)<9:return
            row=tree.identify_row(event.y)
            values=tree.item(row,'values') if row else ()
            if not values:return
            parent=Path(values[0]);parent=parent if parent.is_dir() else parent.parent
            if parent==source.parent:return
            self.perform_file_operation(source,'move',parent/source.name)
        tree.bind('<ButtonPress-1>',press,add='+');tree.bind('<ButtonRelease-1>',release,add='+')
