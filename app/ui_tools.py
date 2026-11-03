from pathlib import Path
import json
import os
import re
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog
from app_dialogs import messagebox
from PIL import Image,ImageDraw,ImageTk
from command_icons import command_icon
from hints import tooltip
from office_forms import instruction
from scanner_ui import scanner

LIGHT=dict(bg='#faf5f1',paper='#fffdfa',text='#312b29',muted='#695b54',line='#e3d8d0',accent='#eac7b4',btn='#f2e6dc',hover='#ecd7c7',sel='#dec0ad',glass='#efe5df')
DARK=dict(bg='#212124',paper='#29292d',text='#f4eeea',muted='#cbc0b9',line='#4c4746',accent='#57473e',btn='#39373b',hover='#d3d1d0',sel='#634b40',glass='#353337')
HELP='Бюро ИД помогает инженеру ПТО заполнить акты по шаблону и проверить печатный вид.\n\n1. На главной выберите документ, папку или ZIP. Рабочие файлы хранятся в папке проекта.\n2. Найдите документ или шаблон в левом дереве. В центре введите свои значения или выберите вариант. PDF справа обновляется после ввода. Ctrl + колесо меняет масштаб.\n3. Для сканов нажмите «Разобрать паспорта», проверьте страницы и реквизиты, затем сохраните.\n4. На панели проекта доступны экспорт текущего документа, сборка просмотренных PDF и печать.\n\nCtrl+C/V/X — копирование, вставка, вырезание. Ctrl+Z/Y — отмена и повтор. Отделённую панель возвращает кнопка «Вернуть».'

class Interface:
    def ui_init(self,store):
        from app_dialogs import configure
        configure(self)
        self.catalog_dir=store/'Библиотека';self.prefs_file=store/'Настройки.json'
        try:self.dark=bool(json.loads(self.prefs_file.read_text('utf-8')).get('dark'))
        except (ValueError,OSError):self.dark=False
        self.theme_images={};self.icons={};self.style=ttk.Style(self.root);self.style.theme_use('clam')
        self.set_palette()
        def hint_on_map(event):
            w=event.widget
            if isinstance(w,(ttk.Button,tk.Button,ttk.Menubutton)):
                label=str(w.cget('text'))
                meanings={'↗':'Отделить панель','—':'Свернуть окно','□':'Развернуть или восстановить окно','Вернуть':'Вернуть панель в рабочую область','×':'Закрыть окно'}
                tooltip(w,meanings.get(label,label))
        self.root.bind('<Map>',hint_on_map,add='+')
        def mapped(event):
            w=event.widget
            if isinstance(w,tk.PanedWindow):
                w.configure(opaqueresize=False,proxybackground=self.colors['accent'],proxyborderwidth=0)
                from glass_resize import install as glass
                glass(w,self)
            if isinstance(w,tk.Toplevel) and not w.overrideredirect():
                from windows_integration import theme_caption
                theme_caption(w,self.colors,self.dark)
                from windows_integration import close_only
                close_only(w)
                detached=w in getattr(self,'windows',{}).values()
                if not detached:
                    from app_dialogs import place_window
                    w.after_idle(lambda target=w:place_window(self,target))
                if detached and self.root.attributes('-fullscreen'):
                    w._fullscreen_owner=True
                    if str(w.transient())!=str(self.root):w.transient(self.root)
                if not detached and not getattr(w,'_taskbar_utility',False) and not getattr(w,'_dialog_owner_set',False):
                    w._dialog_owner_set=True
                    owner=w.master.winfo_toplevel()
                    if owner is not w:
                        w.transient(owner)
                        w.after_idle(lambda target=w:target.lift() if target.winfo_exists() else None)
            if isinstance(w,(tk.Listbox,ttk.Treeview,tk.Text)) or isinstance(w,tk.Canvas) and w.cget('yscrollcommand'):
                from auto_scroll import install as scroll
                scroll(w)
        self.root.bind_all('<Map>',mapped,add='+')
        from resize_preview import install
        install(self.root)
        self._fit_job=None
        def settled(event):
            if event.widget is not self.root:return
            if self._fit_job is not None:self.root.after_cancel(self._fit_job)
            def fit():
                self._fit_job=None;self.enforce_panel_sizes()
            self._fit_job=self.root.after(100,fit)
        self.root.bind('<Configure>',settled,add='+')
    def set_palette(self):
        c=DARK if self.dark else LIGHT;self.colors=c;st=self.style
        st.configure('Context.TLabel',background=c['glass'],foreground=c['muted'],font=('Segoe UI',10),padding=(8,3))
        st.configure('.',background=c['bg'],foreground=c['text'],fieldbackground=c['paper'])
        for n in ['TEntry','TCombobox','TSpinbox','Treeview']:
            st.configure(n,background=c['paper'],foreground=c['text'],fieldbackground=c['paper'],selectbackground=c['sel'],selectforeground=c['text'],insertcolor=c['text'],arrowcolor=c['text'])
            st.map(n,fieldbackground=[('readonly',c['paper'])],foreground=[('readonly',c['text'])],background=[('selected',c['sel'])])
        for name in ('TEntry','TCombobox'):
            entry_bg='#d3d1d0' if self.dark else LIGHT['paper']
            st.configure(name,fieldbackground=entry_bg,foreground=LIGHT['text'],insertcolor=LIGHT['text'])
            st.map(name,fieldbackground=[('readonly',entry_bg),('!disabled',entry_bg)],foreground=[('!disabled',LIGHT['text'])])
        self.root.option_add('*TCombobox*Listbox.background',LIGHT['paper'])
        self.root.option_add('*TCombobox*Listbox.foreground',LIGHT['text'])
        self.root.option_add('*TCombobox*Listbox.font',('Times New Roman',11))
        field=('Dark' if self.dark else 'Light')+'Form.field'
        arrow=('Dark' if self.dark else 'Light')+'Form.arrow'
        entry_bg='#d3d1d0' if self.dark else LIGHT['paper']
        if field not in st.element_names():
            images=[]
            for border in (c['line'],c['accent']):
                im=Image.new('RGB',(20,24),c['paper']);draw=ImageDraw.Draw(im)
                draw.rounded_rectangle((0,0,19,23),radius=5,fill=entry_bg,outline=border)
                images.append(ImageTk.PhotoImage(im,master=self.root))
            self.theme_images[field]=images;st.element_create(field,'image',images[0],('focus',images[1]),border=5,sticky='nsew')
            im=Image.new('RGB',(18,20),entry_bg);ImageDraw.Draw(im).polygon(((5,8),(13,8),(9,12)),fill=LIGHT['text'])
            photo=ImageTk.PhotoImage(im,master=self.root);self.theme_images[arrow]=[photo];st.element_create(arrow,'image',photo,sticky='')
        for kind in ('Entry','Combobox'):
            children=[]
            if kind=='Combobox':children.append((arrow,{'side':'right','sticky':'ns'}))
            children.append((kind+'.padding',{'sticky':'nsew','children':[(kind+'.textarea',{'sticky':'nsew'})]}))
            st.layout('Form.T'+kind,[(field,{'sticky':'nsew','children':children})])
            st.configure('Form.T'+kind,font=('Times New Roman',11),padding=(6,3),fieldbackground=entry_bg,foreground=LIGHT['text'],insertcolor=LIGHT['text'])
            st.map('Form.T'+kind,fieldbackground=[('readonly',entry_bg)],foreground=[('!disabled',LIGHT['text'])])
        st.map('TButton',background=[('active',c['hover'])],foreground=[('disabled',c['muted'])])
        for name in ('TCheckbutton','TRadiobutton'):
            st.map(name,background=[('active',c['bg']),('!disabled',c['bg'])],
                   foreground=[('disabled',c['muted']),('active',c['text']),('!disabled',c['text'])])
        theme='Dark' if self.dark else 'Light'
        for style,normal in [('Action',c['btn']),('Primary',c['accent']),('Tool',None),('Window',None)]:
            element=f'{theme}{style}.surface'
            if element not in st.element_names():
                imgs=[]
                for col in [normal,c['hover'],c['sel']]:
                    # Opaque corner pixels match the parent surface in every
                    # state. Native child-window clipping leaves stale pixels
                    # when Windows moves Tk controls.
                    im=Image.new('RGB',(32,32),c['accent'] if style=='Window' else c['bg']);draw=ImageDraw.Draw(im)
                    if col:
                        if normal:draw.rounded_rectangle((0,1,31,31),radius=8,fill=c['line'])
                        draw.rounded_rectangle((0,0,31,30),radius=8,fill=col,outline=c['line'] if normal else None)
                    if not normal:im=im.resize((20,20),Image.Resampling.LANCZOS)
                    img=ImageTk.PhotoImage(im,master=self.root);imgs.append(img)
                self.theme_images[element]=imgs;st.element_create(element,'image',imgs[0],('pressed',imgs[2]),('active',imgs[1]),border=9 if normal else 5,sticky='nsew')
            st.layout(style+'.TButton',[(element,{'sticky':'nsew','children':[('Button.padding',{'sticky':'nsew','children':[('Button.label',{'sticky':'nsew'})]})]})])
            st.configure(style+'.TButton',foreground=c['text'],background=(c['accent'] if style=='Window' else c['bg']),padding=(3,2) if not normal else (10,6),anchor='center')
            surface=c['accent'] if style=='Window' else c['bg']
            st.map(style+'.TButton',foreground=[('active','#111111'),('!disabled',c['text'])],background=[('pressed',surface),('active',surface),('focus',surface),('!disabled',surface)])
        for heading in ('Treeview.Heading','Package.Treeview.Heading'):
            st.map(heading,foreground=[('active','#111111')],background=[('active','#d3d1d0')])
        element=theme+'Compact.surface'
        if element not in st.element_names():
            imgs=[]
            for fill in (c['btn'],c['hover'],c['sel']):
                im=Image.new('RGB',(28,26),c['bg']);ImageDraw.Draw(im).rounded_rectangle((0,0,27,25),radius=5,fill=fill,outline=c['line'])
                imgs.append(ImageTk.PhotoImage(im,master=self.root))
            self.theme_images[element]=imgs;st.element_create(element,'image',imgs[0],('pressed',imgs[2]),('active',imgs[1]),border=6,sticky='nsew')
        st.layout('Compact.TButton',[(element,{'sticky':'nsew','children':[('Button.padding',{'sticky':'nsew','children':[('Button.label',{'sticky':'nsew'})]})]})])
        st.configure('Compact.TButton',padding=(7,0),foreground=c['text'],background=c['bg'])
        st.map('Compact.TButton',background=[('!disabled',c['bg'])])
        st.map('Compact.TButton',foreground=[('disabled',c['muted']),('pressed',c['text']),('active','#111111'),('!disabled',c['text'])])
        st.configure('Strip.TFrame',background=c['glass'])
    def paint(self,widget):
        c=self.colors
        def walk(w):
            if isinstance(w,(tk.Tk,tk.Toplevel)) and not w.overrideredirect():
                from windows_integration import theme_caption
                theme_caption(w,c,self.dark)
            if isinstance(w,(ttk.Entry,ttk.Combobox)):
                w.configure(style='Form.TCombobox' if isinstance(w,ttk.Combobox) else 'Form.TEntry',font=('Times New Roman',11))
                from clipboard_keys import install as clipboard_install
                clipboard_install(w)
                from drag_selection import install
                install(w)
                if isinstance(w,ttk.Combobox) and not getattr(w,'focus_selection_installed',False):
                    w.focus_selection_installed=True
                    def selected(e):
                        field=e.widget
                        if getattr(field,'preserve_segment_selection',False) or str(field.cget('state'))=='readonly':return
                        field.focus_set();field.icursor('end');field.selection_range(0,'end');field.xview('end')
                    w.bind('<<ComboboxSelected>>',selected,add='+')
            if isinstance(w,(ttk.Button,tk.Button,ttk.Menubutton)):
                text=str(w.cget('text'))
                hints={'↗':'Отделить панель в самостоятельное окно','—':'Свернуть окно','□':'Развернуть или восстановить размер','Вернуть':'Вернуть панель в рабочую область','×':'Закрыть окно'}
                tooltip(w,hints.get(text,text))
            if hasattr(w,'icon_name'):w.configure(image=self.icon(w.icon_name))
            if isinstance(w,ttk.Button):
                if not getattr(w,'surface_hover',False):
                    w.surface_hover=True
                    w.bind('<Enter>',lambda e:e.widget.state(['active']),add='+')
                    w.bind('<Leave>',lambda e:e.widget.state(['!active']),add='+')
                if not getattr(w,'window_button',False) and w.cget('style') in ('','TButton','Action.TButton'):
                    w.configure(style='Compact.TButton')
                    if str(w.cget('text')).strip() and not w.cget('image'):
                        text=str(w.cget('text')).casefold()
                        key=next((icon for word,icon in [('удал','delete'),('отмен','undo'),('сохран','save'),('паспорт','passports'),('каталог','catalog'),('откры','import'),('проект','folder'),('копир','copy')] if word in text),'checkall')
                        w.icon_name=key;w.configure(image=self.icon(key),compound='left')
                        from hints import hover_icon
                        hover_icon(w,self,key)
            if isinstance(w,tk.Scale):w.configure(bg=c['bg'],fg=c['text'],troughcolor=c['line'],activebackground=c['hover'])
            if isinstance(w,(tk.Frame,tk.Label,tk.Button,tk.Listbox,tk.Canvas,tk.PanedWindow,tk.Toplevel,tk.Tk)) and 'background' in w.keys():
                if w is getattr(self,'canvas',None):return
                old=str(w.cget('background'))
                name=getattr(w,'tone',None)
                if name is None:
                    name='paper' if old.lower() in ('#fffdfa','#ffffff','white') else 'accent' if old.lower() in ('#eac7b4','#f6eee8') else 'line' if isinstance(w,tk.PanedWindow) else 'bg'
                    w.tone=name
                w.configure(bg=c[name])
                if isinstance(w,(tk.Label,tk.Button,tk.Listbox)):w.configure(fg=c['text'])
                if isinstance(w,tk.Button):w.configure(activebackground=c['hover'],activeforeground='#111111')
                if isinstance(w,tk.Listbox):w.configure(selectbackground=c['sel'],selectforeground=c['text'])
            if hasattr(w,'redraw_theme'):w.redraw_theme()
            for child in w.winfo_children():walk(child)
        if widget.winfo_exists():walk(widget)
    def toggle_theme(self,value):
        self.dark=bool(int(float(value)));self.set_palette()
        self.prefs_file.write_text(json.dumps({'dark':self.dark}),'utf-8');self.paint(self.root)
        for glass in getattr(self,'glass_widgets',[]):
            if glass.winfo_exists():glass.event_generate('<Configure>',width=glass.winfo_width())
        for switch in getattr(self,'theme_switches',[]):
            if switch.winfo_exists() and switch.get()!=int(self.dark):switch.set(int(self.dark))
    def icon(self,key):
        pair=(self.dark,key)
        if pair not in self.icons:self.icons[pair]=command_icon(self.root,key,self.colors['text'])
        return self.icons[pair]
    def window_ribbon(self,window):
        """Utilities use panel-sized glyphs and native taskbar minimization."""
        from windows_integration import normal_window
        window._taskbar_utility=True
        window.transient('');normal_window(window)
        row=tk.Frame(window,bg=self.colors['accent']);row.tone='accent';row.pack(fill='x')
        window.utility_ribbon=row
        window.bind('<Escape>',self.escape_full,add='+')
        def restore():
            window.deiconify();window.lift()
        def hide():
            window.iconify()
        # The exact same text glyphs, spacing and ttk surface as pane_header.
        for label,action in [('□',lambda:self.maximize(window)),('—',hide)]:
            ttk.Button(row,text=label,command=action,style='Window.TButton',width=2,takefocus=False).pack(side='right')
        window.utility_actions=dict(hide=hide,restore=restore)
        return row
    def icon_button(self,parent,key,label,action,dropdown=False):
        # Paint the entire icon cell against its actual parent. Native ttk buttons
        # otherwise show a rectangular themed background outside the rounded surface.
        width=39 if dropdown else 29
        btn=tk.Canvas(parent,width=width,height=27,bd=0,highlightthickness=0,takefocus=True,cursor='hand2')
        btn.pack(side='left',padx=1);state={'hover':False,'press':False}
        def redraw():
            c=self.colors
            bg=parent.cget('background') if isinstance(parent,tk.Frame) else self.style.lookup(parent.cget('style') or 'TFrame','background') or c['bg']
            btn.configure(bg=bg)
            im=Image.new('RGB',(width*3,81),bg)
            if state['hover'] or state['press'] or btn.focus_get()==btn:
                ImageDraw.Draw(im).rounded_rectangle((2,2,width*3-3,78),radius=18,fill=c['sel'] if state['press'] else c['hover'])
            btn.back=ImageTk.PhotoImage(im.resize((width,27),Image.Resampling.LANCZOS));btn.delete('all')
            btn.create_image(0,0,anchor='nw',image=btn.back);btn.hover_glyph=command_icon(self.root,getattr(btn,'glyph',key),'#111111') if state['hover'] and not state['press'] else self.icon(getattr(btn,'glyph',key));btn.create_image(14,13,image=btn.hover_glyph)
            if dropdown:btn.create_polygon(27,11,33,11,30,15,fill=c['text'])
        btn.redraw_theme=redraw;redraw()
        def dispose(event):
            if event.widget is btn:
                btn.back=None;btn.hover_glyph=None;btn.redraw_theme=lambda:None
        btn.bind('<Destroy>',dispose,add='+')
        def enter_icon(e):state['hover']=True;redraw()
        def leave_icon(e):state.update(hover=False,press=False);redraw()
        def down(e):state['press']=True;redraw()
        def up(e):
            pressed=state['press'];state['press']=False;redraw()
            if pressed and 0<=e.x<width and 0<=e.y<27:action()
        for evt,fn in [('<Enter>',enter_icon),('<Leave>',leave_icon),('<ButtonPress-1>',down),('<ButtonRelease-1>',up),('<FocusIn>',lambda e:redraw()),('<FocusOut>',lambda e:redraw()),('<space>',lambda e:action()),('<Return>',lambda e:action())]:
            btn.bind(evt,fn)
        tooltip(btn,label)
        return btn
    def commands(self,host):
        row=ttk.Frame(host,padding=(8,4),style='Strip.TFrame');row.pack(fill='x')
        self.command_rows=[w for w in getattr(self,'command_rows',[]) if w.winfo_exists()]+[row]
        self.root.after_idle(self.enforce_panel_sizes)
        in_editor=host is getattr(self,'header',None)
        if in_editor:self.icon_button(row,'home','Мои проекты',self.home)
        menu=tk.Menu(row,tearoff=False)
        def popup():
            c=self.colors
            menu.configure(background=c['paper'],foreground=c['text'],activebackground=c['hover'],activeforeground='#111111')
            try:menu.tk_popup(btn.winfo_rootx(),btn.winfo_rooty()+btn.winfo_height())
            finally:menu.grab_release()
        btn=self.icon_button(row,'import','Импорт · выбрать источник',popup,True)
        if in_editor:
            menu.add_command(label='Добавить документ в этот проект…',command=self.choose)
            menu.add_command(label='Результаты анализа документов…',command=lambda:self.analysis_report(self.project))
            menu.add_separator()
        for kind,label in [('file','Новый проект из документа…'),('folder','Новый проект из папки…'),('zip','Новый проект из ZIP…')]:
            menu.add_command(label=label,command=lambda k=kind:self.import_item(k))
        for key,label,fn in [('export','Экспорт документа',self.export_current),('assemble','Собрать PDF',self.assemble),('print','Печать',self.print_current),('help','Краткое руководство',lambda:messagebox.showinfo('Бюро ИД · Помощь',HELP))]:
            self.icon_button(row,key,label,fn)
        if in_editor:
            ttk.Separator(row,orient='vertical').pack(side='left',fill='y',padx=4)
            self.toolbar(row,None,inline=True)
        ttk.Separator(row,orient='vertical').pack(side='left',fill='y',padx=6)
        self.style.configure('Context.TLabel',background=self.colors['glass'],foreground=self.colors['muted'],font=('Segoe UI',10),padding=(8,3))
        ttk.Label(row,style='Context.TLabel',text=(self.project.name if len(self.project.name)<=30 else self.project.name[:27]+'…') if in_editor else 'Проекты').pack(side='left',padx=3)
        moon=self.icon_button(row,'moon','Тёмная тема',lambda:self.toggle_theme(1));moon.pack_forget();moon.pack(side='right')
        self.toggle_control(row)
        sun=self.icon_button(row,'sun','Светлая тема',lambda:self.toggle_theme(0));sun.pack_forget();sun.pack(side='right')
        mode='restore' if self.root.attributes('-fullscreen') else 'fullscreen'
        full=self.icon_button(row,mode,'Полный экран / восстановить · Esc',self.toggle_fullscreen)
        full.pack_forget();full.pack(side='right',padx=4)
        self.full_buttons=[w for w in getattr(self,'full_buttons',[]) if w.winfo_exists()]+[full]
        self.root.bind('<Escape>',self.escape_full,add=False)

    def toggle_fullscreen(self):
        from ui_surface import transition,repaint
        from windows_integration import monitor_bounds,cover_monitor
        active=not self.root.attributes('-fullscreen')
        from taskbar_reveal import install as taskbar_install
        taskbar_install(self.root)
        if not hasattr(self,'_full_safe'):
            self._full_safe=tk.Frame(self.root,height=26,bg=self.colors['bg']);self._full_safe.tone='bg'
        if active:self._full_safe.pack(side='bottom',fill='x',before=self.root.winfo_children()[0])
        else:self._full_safe.pack_forget()
        if not active:self.root.taskbar_reveal['reset']()
        def apply():
            if active:
                self._before_full=(self.root.geometry(),self.root.state());bounds=monitor_bounds(self.root)
                self.root.attributes('-fullscreen',True)
                self.root.after_idle(lambda:cover_monitor(self.root,bounds))
            else:
                self.root.attributes('-fullscreen',False)
                if hasattr(self,'_before_full'):
                    geometry,state=self._before_full
                    self.root.state('normal')
                    if getattr(self.root,'app_caption',None):self.root.app_caption.reconcile()
                    self.root.geometry(geometry)
                    if state!='zoomed':
                        from ui_surface import restore_client_size
                        self.root.after_idle(lambda:restore_client_size(self.root,geometry))
                    if state=='zoomed':self.root.state('zoomed')
        transition(self.root,apply)
        for w in self.full_buttons:
            if w.winfo_exists():w.glyph='restore' if active else 'fullscreen';w.redraw_theme()
        for window in getattr(self,'windows',{}).values():
            window._fullscreen_owner=active
            window.transient(self.root if active else '')
            if active:self.root.after(30,lambda w=window:w.lift() if w.winfo_exists() else None)
        self.root.after_idle(lambda:repaint(self.root))
    def escape_full(self,event=None):
        window=event.widget.winfo_toplevel() if event is not None else self.root
        if window is not self.root and window.attributes('-fullscreen'):
            self.maximize(window);return 'break'
        if self.root.attributes('-fullscreen'):self.toggle_fullscreen();return 'break'
    def limit_home_layout(self):
        layout=getattr(self,'home_layout',None)
        if not layout or not self.landing.winfo_exists() or not self.landing.winfo_manager():return
        panes,sidebar,right,center=layout
        if not panes.winfo_exists():return
        # The right pane contains two distinct blocks. Reserve room for both,
        # including their packing margins, before allowing the library to grow.
        card=next((child for child in right.winfo_children() if child is not center),None)
        card_min=max(210,card.winfo_reqwidth() if card is not None else 210)+24
        labels=[child.winfo_reqwidth() for child in center.winfo_children() if isinstance(child,(tk.Label,ttk.Label))]
        center_min=max([340]+labels)+80
        right_min=card_min+center_min
        left_min=260
        panes.paneconfigure(sidebar,minsize=left_min)
        panes.paneconfigure(right,minsize=right_min)
        top=max((w.winfo_reqwidth() for w in getattr(self,'command_rows',[]) if w.winfo_exists()),default=820)
        self.root.minsize(max(top,left_min+right_min+12),500)
        if panes.winfo_width()>left_min+right_min:
            x,y=panes.sash_coord(0)
            maximum=panes.winfo_width()-right_min-int(panes.cget('sashwidth'))-4
            desired=max(left_min,min(x,maximum))
            if desired!=x:panes.sash_place(0,desired,y)
    def enforce_panel_sizes(self):
        if not self.root.winfo_exists():return
        if getattr(self,'landing',None) is not None and self.landing.winfo_exists() and self.landing.winfo_manager():
            self.limit_home_layout();return
        top=max((w.winfo_reqwidth() for w in getattr(self,'command_rows',[]) if w.winfo_exists()),default=820)
        if not hasattr(self,'holders') or not all(n in self.holders for n in (0,1,2,3)):
            self.root.minsize(max(820,top),480);return
        widths={}
        for n,host in self.holders.items():
            actual=getattr(self,'windows',{}).get(n,host)
            # Only the controls determine a minimum. Tree/content requests grow
            # with a stretched pane and must never become its new lower limit.
            widths[n]=180
            # Reserve the complete header and toolbar, including pack margins.
            for row in actual.winfo_children():
                if not (getattr(row,'panel_header',False) or getattr(row,'panel_toolbar',False)):continue
                children=[c for c in row.winfo_children() if c.winfo_manager()=='pack']
                if children and all(c.pack_info().get('side') in ('left','right') for c in children):
                    required=0
                    for c in children:
                        pad=c.pack_info().get('padx',0)
                        values=list(pad) if isinstance(pad,(tuple,list)) else str(pad).split();margin=sum(int(float(x)) for x in values) if len(values)>1 else 2*int(float(values[0]))
                        required+=c.winfo_reqwidth()+margin
                    widths[n]=max(widths[n],required+8)
            widths[n]=max(180,widths[n]+8)
            if n in self.windows:
                window=self.windows[n];window.minsize(widths[n],200)
                if window.state()=='normal' and window.winfo_width()<widths[n]:window.geometry(f'{widths[n]}x{max(200,window.winfo_height())}')
        left=self.holders[0].master
        if left is not self.split:
            left_min=max(widths[0],widths[3])
            options=dict(minsize=left_min)
            if left.winfo_width()<left_min:options['width']=left_min
            self.split.paneconfigure(left,**options)
            # A saved explicit width can override an early sash_place during
            # Tk's first geometry pass. The next mapped pass must check it too.
            if left.winfo_width()<left_min and not getattr(self,'_left_fit_retry',False):
                self._left_fit_retry=True
                def retry():
                    self._left_fit_retry=False;self.enforce_panel_sizes()
                self.root.after(60,retry)
        for n in (1,2):self.split.paneconfigure(self.holders[n],minsize=widths[n])
        minimum=max(top,max(widths[0],widths[3])+widths[1]+widths[2]+24)
        self.root.minsize(minimum,480)
        if self.root.state()=='normal' and not self.root.attributes('-fullscreen') and self.root.winfo_width()<minimum:self.root.geometry(f'{minimum}x{max(480,self.root.winfo_height())}')
        if self.split.winfo_width()>=max(widths[0],widths[3])+widths[1]+widths[2]+16:
            x,y=self.split.sash_coord(0);first=max(widths[0],widths[3]);maximum=self.split.winfo_width()-widths[1]-widths[2]-16;self.split.sash_place(0,max(first,min(x,maximum)),y)
            x,y=self.split.sash_coord(1);first_x=self.split.sash_coord(0)[0];target=max(x,first_x+widths[1]+8)
            target=min(target,self.split.winfo_width()-widths[2]-8);self.split.sash_place(1,target,y)
    def active_file(self):
        s=self.current
        if not s or not self.project or not s.copy.is_relative_to(self.project):
            messagebox.showinfo('Бюро ИД','Откройте документ проекта.');return None
        if self.saved_rev.get(s,-1)!=self.revisions.get(s) or s not in self.latest or s.validated_revision!=self.revisions.get(s):
            messagebox.showinfo('Бюро ИД','Дождитесь обновления предпросмотра.');return None
        if s.formula_errors:messagebox.showerror('Проверка формул','Исправьте ошибки формул: '+', '.join(s.formula_errors));return None
        return s
    def export_current(self):
        import shutil
        s=self.active_file()
        if not s:return
        dest=filedialog.asksaveasfilename(initialfile=s.source.name,defaultextension=s.copy.suffix,filetypes=[('Рабочий документ','*'+s.copy.suffix),('PDF','*.pdf')])
        if dest:
            try:
                if Path(dest).suffix.lower()=='.pdf':Path(dest).write_bytes(self.latest[s])
                else:shutil.copy2(s.copy,dest)
            except OSError as e:messagebox.showerror('Экспорт',str(e))
    def print_current(self):
        s=self.active_file()
        if s:
            directory=Path(tempfile.mkdtemp(prefix='bureau-print-'));p=directory/(s.source.stem+'.pdf');p.write_bytes(self.latest[s])
            try:os.startfile(p,'print')
            except OSError:os.startfile(p);messagebox.showinfo('Печать','Выберите «Печать» в просмотрщике PDF.')
    def assemble(self):
        from package_build import PackageDialog
        if not self.project or not (self.project/'Документы').is_dir():
            messagebox.showinfo('Сборка','Выберите проект на главной странице.');return
        PackageDialog(self)
    def store_passports(self,folder,meta):
        records=[{**m,'file':str(folder/m['file'])} for m in meta]
        self.merge_quality_records(records)
        if hasattr(self,'body') and 0 in self.body:self.build(0)
    def scan_card(self,host):
        card=ttk.Frame(host,padding=16);card.pack(side='right',fill='y',padx=12,pady=18)
        ttk.Label(card,text='Документы качества',font=('Segoe UI',13,'bold')).pack(anchor='w',pady=4)
        ttk.Label(card,text='PDF, сканы и архивы ZIP',wraplength=185).pack(anchor='w',pady=5)
        from app_dialogs import action
        action(self,card,'Разобрать паспорта','passports',lambda:scanner(self)).pack(anchor='w')
        action(self,card,'Каталог документов','catalog',self.show_catalog).pack(anchor='w',pady=4)
    def show_catalog(self):
        cat=self.catalog_dir/'Документы качества.json'
        win=tk.Toplevel(self.root);win.title('Библиотека · Документы качества')
        table=ttk.Treeview(win,columns=('type','number','date','material'),show='headings');table.pack(fill='both',expand=True)
        for k,name in zip(table['columns'],('Документ','Номер','Дата','Материал')):table.heading(k,text=name)
        data=json.loads(cat.read_text('utf-8')) if cat.exists() else []
        for i,m in enumerate(data):table.insert('','end',iid=str(i),values=[m[k] for k in table['columns']])
        def view(e):
            if table.selection():
                path=Path(data[int(table.selection()[0])]['file'])
                if path.exists():os.startfile(path)
        table.bind('<Double-1>',view);self.paint(win)




