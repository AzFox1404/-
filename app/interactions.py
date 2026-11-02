from pathlib import Path
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image,ImageDraw,ImageTk
from win_drop import accept_files

class Interactions:
    def recent_list(self,root):
        file=root.parent/'Недавние.json'
        if file.exists():
            try:return [Path(p) for p in json.loads(file.read_text('utf-8'))][:3]
            except (ValueError,OSError):pass
        return sorted((p for p in root.iterdir() if (p/'project.json').is_file()),key=lambda p:p.stat().st_mtime,reverse=True)[:3]
    def touch_recent(self,project):
        recent=[project]+[p for p in self.recent_list(project.parent) if p!=project]
        file=project.parent.parent/'Недавние.json'
        tmp=file.with_suffix('.tmp');tmp.write_text(json.dumps(list(map(str,recent[:3])),ensure_ascii=False),'utf-8');tmp.replace(file)
    def project_browser(self,root):
        win=tk.Toplevel(self.root);win.title('Проекты на компьютере')
        items=sorted(p for p in root.iterdir() if (p/'project.json').is_file())
        lst=tk.Listbox(win,width=50,height=12);lst.pack(fill='both',expand=True)
        for p in items:lst.insert('end',p.name)
        def use():
            if lst.curselection():
                path=items[lst.curselection()[0]];win.destroy();self.enter(path)
        lst.bind('<Double-1>',lambda e:use());ttk.Button(win,text='Открыть',command=use).pack(pady=5);self.paint(win)
    def source_zone(self,parent):
        zone=tk.Canvas(parent,height=190,bd=0,highlightthickness=0,cursor='hand2')
        zone.pack(fill='x',pady=18)
        def choose():
            options=tk.Menu(zone,tearoff=False,bg=self.colors['paper'],fg=self.colors['text'],activebackground=self.colors['hover'],activeforeground='#111111')
            def pick():
                paths=filedialog.askopenfilenames(filetypes=[('Документы и ZIP','*.doc *.docx *.xls *.xlsx *.zip')])
                if paths:self.drop_inputs(list(map(Path,paths)))
            options.add_command(label='Документы или архив ZIP…',command=pick)
            options.add_command(label='Папка с документами…',command=lambda:self.import_item('folder'))
            try:options.tk_popup(zone.winfo_rootx()+zone.winfo_width()//2-70,zone.winfo_rooty()+130)
            finally:options.grab_release()
        def redraw(*_):
            c=self.colors;w=max(160,zone.winfo_width());zone.configure(bg=c['bg']);zone.delete('all')
            zone.create_rectangle(6,6,w-6,182,outline=c['muted'],dash=(5,4),width=1,fill=c['paper'])
            zone.create_text(w/2,43,text='↑',font=('Segoe UI',24,'bold'),fill=c['text'])
            zone.create_text(w/2,83,text='Перетащите документы, папку или архив сюда',width=w-32,justify='center',font=('Segoe UI',12),fill=c['text'])
            zone.create_text(w/2,118,text='Выбрать на компьютере…',font=('Segoe UI',11,'bold'),fill=c['text'])
            zone.create_text(w/2,153,text='Word · Excel · ZIP',fill=c['muted'])
        zone.bind('<Configure>',redraw);zone.bind('<Button-1>',lambda e:choose())
        zone.bind('<Return>',lambda e:choose());zone.configure(takefocus=True);zone.redraw_theme=redraw
        accept_files(zone,self.drop_inputs)
    def drop_inputs(self,paths):
        if not paths:return
        first=paths[0]
        if len(paths)>1 and any(p.suffix.lower() not in ('.doc','.docx','.xls','.xlsx') or not p.is_file() for p in paths):
            messagebox.showinfo('Источник','Выберите одну папку, один архив или несколько документов.');return
        if first.is_dir():kind='folder'
        elif first.suffix.lower()=='.zip':kind='zip'
        elif first.suffix.lower() in ('.doc','.docx','.xls','.xlsx'):kind='file'
        else:messagebox.showinfo('Источник','Поддерживаются Word, Excel, папки и ZIP.');return
        old=self.project;self.import_item(kind,first)
        if self.project is not old:
            for p in paths[1:]:self.add_copy(p)
    def toggle_control(self,row):
        toggle=tk.Canvas(row,width=40,height=22,highlightthickness=0,bd=0,takefocus=True,cursor='hand2')
        toggle.pack(side='right',padx=3)
        def redraw():
            c=self.colors;bg=c['glass'];im=Image.new('RGB',(160,88),bg)
            d=ImageDraw.Draw(im)
            d.rounded_rectangle((4,7,156,81),radius=37,fill=('#a47763' if self.dark else '#c9b9b0'))
            x=84 if self.dark else 12
            d.ellipse((x,13,x+61,74),fill='#fffaf7')
            toggle.picture=ImageTk.PhotoImage(im.resize((40,22),Image.Resampling.LANCZOS),master=self.root)
            toggle.configure(bg=bg);toggle.delete('all');toggle.create_image(0,0,anchor='nw',image=toggle.picture)
        toggle.redraw_theme=redraw;redraw()
        toggle.bind('<Button-1>',lambda e:self.toggle_theme(not self.dark))
        toggle.bind('<space>',lambda e:self.toggle_theme(not self.dark))
    def form_mouse(self,panel):
        def scroll(e):
            canvas=getattr(self,'form_canvas',None)
            if canvas and canvas.winfo_exists():canvas.yview_scroll(-int(e.delta/120) or (-1 if e.delta>0 else 1),'units')
            return 'break'
        def escape(e):
            panel.focus_set()
            if self.root.attributes('-fullscreen'):self.toggle_fullscreen()
            return 'break'
        self.root.bind_class('FormNavigation','<MouseWheel>',scroll)
        self.root.bind_class('FormNavigation','<Escape>',escape)
        def middle(e):
            from auto_scroll import install
            from types import SimpleNamespace
            canvas=getattr(self,'form_canvas',None)
            if not canvas or not canvas.winfo_exists():return
            install(canvas)
            return canvas.toggle_auto_scroll(SimpleNamespace(x=e.x_root-canvas.winfo_rootx(),y=e.y_root-canvas.winfo_rooty(),x_root=e.x_root,y_root=e.y_root))
        self.root.bind_class('FormNavigation','<Button-2>',middle)
        def arrow(e):
            if isinstance(e.widget,(tk.Entry,ttk.Entry,ttk.Combobox,tk.Text,ttk.Spinbox)):return
            canvas=getattr(self,'form_canvas',None)
            if canvas and canvas.winfo_exists():canvas.yview_scroll(-1 if e.keysym=='Up' else 1,'units')
            return 'break'
        self.root.bind_class('FormNavigation','<Up>',arrow)
        self.root.bind_class('FormNavigation','<Down>',arrow)
        def visit(w):
            w.bindtags(('FormNavigation',)+tuple(t for t in w.bindtags() if t!='FormNavigation'))
            if isinstance(w,ttk.Combobox):
                pop=w.tk.call('ttk::combobox::PopdownWindow',str(w))
                lb=str(pop)+'.f.l'
                if int(w.tk.call('winfo','exists',lb)):
                    # Scroll the list viewport. Commit only on a deliberate selection.
                    w.tk.call('bind',lb,'<Escape>',f'ttk::combobox::Unpost {w}; focus {panel}; break')
                    w.tk.call('bind',lb,'<MouseWheel>',f'{lb} yview scroll [expr {{%D > 0 ? -3 : 3}}] units; break')
            for child in w.winfo_children():visit(child)
        visit(panel)
    def drag_from_library(self,tree,on_home):
        drag=[None]
        def press(e):
            sel=tree.identify_row(e.y)
            vals=tree.item(sel,'values') if sel else ()
            drag[0]=(e.x_root,e.y_root,Path(vals[0])) if vals else None
        def release(e):
            if not drag[0]:return
            x,y,p=drag[0];drag[0]=None
            if abs(x-e.x_root)+abs(y-e.y_root)<8:return
            w=self.root.winfo_containing(e.x_root,e.y_root)
            while w:
                if on_home and hasattr(w,'recent_project'):
                    project=w.recent_project
                    if (project/'project.json').is_file():self.enter(project);self.add_copy(p)
                    return
                if not on_home and w in (self.holders.get(0),self.windows.get(0)):
                    self.add_copy(p);return
                w=w.master
        tree.bind('<ButtonPress-1>',press,add='+');tree.bind('<ButtonRelease-1>',release,add='+')

