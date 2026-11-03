"""Review document boundaries and metadata before exporting independent PDFs."""
from smooth_scrollbar import Scrollbar
import json
from pathlib import Path
import queue
import threading
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog
from app_dialogs import messagebox
from passports import save_records,TYPES
from passport_process import inspect

def scanner(app,files=None,destination=None):
    if files is None:files=filedialog.askopenfilenames(parent=app.root,title='Паспорта и сертификаты',filetypes=[('PDF, JPEG или ZIP','*.pdf *.jpg *.jpeg *.zip')])
    if not files:return
    if getattr(app,'active_scan',None) and app.active_scan.winfo_exists():app.active_scan.focus_set();return
    win=tk.Toplevel(app.root);win.title('Разбор паспортов и сертификатов');win.geometry('1050x680');win.minsize(780,620)
    app.active_scan=win
    app.window_ribbon(win)
    status=tk.StringVar(value='Чтение документов…');notice=ttk.Label(win,textvariable=status,padding=12,wraplength=980);notice.pack(fill='x')
    win.bind('<Configure>',lambda e:notice.configure(wraplength=max(200,e.width-28)) if e.widget is win else None,add='+')
    tmp=tempfile.TemporaryDirectory();events=queue.Queue();cancelled=threading.Event()
    def notify(s):
        if cancelled.is_set():raise RuntimeError('Отменено пользователем')
        events.put(('status',s))
    cache=app.catalog_dir/'Кэш распознавания'
    def work():
        try:events.put(('ready',inspect(list(map(Path,files)),Path(tmp.name),notify,cache,cancelled)))
        except Exception as exc:events.put(('error',str(exc)))
        finally:
            if cancelled.is_set():tmp.cleanup()
    threading.Thread(target=work,daemon=True).start()
    win.protocol('WM_DELETE_WINDOW',lambda:(cancelled.set(),win.destroy()))
    def poll():
        if cancelled.is_set() or not win.winfo_exists():return
        while not events.empty():
            kind,data=events.get()
            if cancelled.is_set():
                if kind!='status':tmp.cleanup();return
                continue
            if kind=='status':status.set(data)
            elif kind=='error':
                tmp.cleanup();win.destroy();messagebox.showerror('Распознавание',data);return
            else:
                if not data:
                    tmp.cleanup();win.destroy();messagebox.showerror('Распознавание','В источнике нет документов.');return
                try:review(data)
                except Exception as exc:
                    win.destroy();tmp.cleanup();messagebox.showerror('Просмотр паспортов',str(exc))
                return
        win.after(100,poll)
    def review(records):
        status.set('Проверьте границы страниц, номер и дату. Нераспознанные значения можно дописать.')
        win.protocol('WM_DELETE_WINDOW',lambda:(win.destroy(),tmp.cleanup()))
        content=tk.PanedWindow(win,orient='horizontal',opaqueresize=False,sashwidth=6);content.pack(fill='both',expand=True)
        left=ttk.Frame(content);right=ttk.Frame(content);content.add(left,minsize=300,width=410,stretch='always');content.add(right,minsize=280,stretch='always')
        listing=ttk.Frame(left);listing.pack(fill='both',expand=True,padx=8)
        lb=tk.Listbox(listing,height=7,exportselection=False)
        list_y=Scrollbar(listing,orient='vertical',command=lb.yview)
        list_x=Scrollbar(listing,orient='horizontal',command=lb.xview)
        lb.configure(yscrollcommand=list_y.set,xscrollcommand=list_x.set)
        listing.rowconfigure(0,weight=1);listing.columnconfigure(0,weight=1)
        lb.grid(row=0,column=0,sticky='nsew');list_y.grid(row=0,column=1,sticky='ns');list_x.grid(row=1,column=0,sticky='ew')
        from pdf_page_preview import PagePreview
        state=[0];vars={}
        preview=PagePreview(right,app);preview.pack(fill='both',expand=True)
        def keep_tools_visible(e=None):
            def clamp():
                if not content.winfo_exists():return
                minimum=max(280,preview.winfo_children()[0].winfo_reqwidth()+12)
                value,y=content.sash_coord(0);limit=content.winfo_width()-minimum
                content.sash_place(0,max(300,min(value,limit)),y)
            content.after_idle(clamp)
        content.bind('<B1-Motion>',keep_tools_visible,add='+')

        def render():
            record=records[state[0]]
            preview.show(record['path'],record['start']-1,record.setdefault('rotations',{}))
        for key,label in [('start','С первой страницы'),('end','По страницу'),('type','Название документа'),('number','Номер'),('date','Дата документа'),('material','Материал')]:
            ttk.Label(left,text=label).pack(anchor='w',padx=8)
            v=tk.StringVar();vars[key]=v
            (ttk.Combobox(left,values=TYPES,textvariable=v) if key=='type' else ttk.Entry(left,textvariable=v)).pack(fill='x',padx=8,pady=2)
        def commit():
            r=records[state[0]];updated={k:v.get().strip() for k,v in vars.items()}
            updated['start']=int(updated['start']);updated['end']=int(updated['end'])
            if not 1<=updated['start']<=updated['end']<=len(r['pages']) or not updated['type']:raise ValueError('Проверьте название и диапазон страниц.')
            if updated['date']:
                from datetime import datetime
                datetime.strptime(updated['date'],'%d.%m.%Y')
            r.update(updated)
        def load(n):
            state[0]=n;r=records[n]
            for k,v in vars.items():v.set(str(r[k]))
            render()
        def refresh():
            lb.delete(0,'end')
            for r in records:lb.insert('end',('☑ ' if r.get('enabled',True) else '☐ ')+f"{r['source']} · {r['start']}–{r['end']} · {r['type']} {r['number']}")
            lb.selection_set(state[0]);lb.see(state[0])
        def pick(e):
            if not lb.curselection():return
            if lb.curselection()[0]==state[0]:return
            try:commit();load(lb.curselection()[0])
            except Exception as exc:messagebox.showerror('Карточка',str(exc));refresh()
        lb.bind('<<ListboxSelect>>',pick)
        def navigate(step):
            try:
                commit();target=max(0,min(len(records)-1,state[0]+step));load(target);refresh()
            except Exception as exc:messagebox.showerror('Карточка',str(exc))
        def mark_all(enabled):
            for record in records:record['enabled']=enabled
            refresh()
        def toggle_record(e=None):
            i=lb.nearest(e.y) if e is not None and hasattr(e,'y') else state[0]
            if not 0<=i<len(records):return 'break'
            records[i]['enabled']=not records[i].get('enabled',True);refresh();return 'break'
        def click_mark(e):
            lb.focus_set()
            if e.x<24:return toggle_record(e)
        lb.bind('<Button-1>',click_mark,add='+');lb.bind('<space>',lambda e:toggle_record())
        lb.bind('<Up>',lambda e:(navigate(-1),'break')[1]);lb.bind('<Down>',lambda e:(navigate(1),'break')[1])
        from keyboard_navigation import install as arrow_navigation
        arrow_navigation(win,navigate)
        nav=win.utility_ribbon
        for key,label,fn in [('up','Предыдущий документ',lambda:navigate(-1)),('down','Следующий документ',lambda:navigate(1)),('checkall','Отметить все документы',lambda:mark_all(True)),('uncheckall','Снять все отметки',lambda:mark_all(False))]:app.icon_button(nav,key,label,fn)

        def split():
            try:
                commit();n=preview.number+1;path=records[state[0]]['path']
                # The continuous preview covers the source PDF, including pages
                # already assigned to neighbouring recognized documents.
                idx=next((i for i,r in enumerate(records) if r['path']==path and r['start']<=n<=r['end']),None)
                if idx is None:raise ValueError('Текущая страница не входит в диапазоны документов. Проверьте границы страниц.')
                r=records[idx]
                if n==r['start']:
                    load(idx);refresh()
                    status.set(f'Страница {n} уже является началом отдельного документа. Для нового разделения прокрутите до следующей нужной страницы.')
                    return
                part=dict(r,start=n,type='Документ',number='',date='',material='');r['end']=n-1
                records.insert(idx+1,part);load(idx+1);refresh()
                status.set(f'Документ разделён перед страницей {n}. Проверьте реквизиты нового документа и сохраните результат.')
            except Exception as exc:messagebox.showerror('Разделение',str(exc))
        def merge():
            try:
                commit();idx=state[0];r=records[idx];other=records[idx+1]
                if other['path']!=r['path']:raise ValueError('Это разные исходные файлы.')
                r['end']=other['end'];records.pop(idx+1);load(idx);refresh()
            except (ValueError,IndexError) as exc:messagebox.showerror('Объединение',str(exc))
        saving=[False]
        def finish():
            if saving[0]:return
            try:
                commit()
                for path in set(r['path'] for r in records):
                    part=[r for r in records if r['path']==path]
                    covered=[i for r in part for i in range(r['start'],r['end']+1)]
                    if sorted(covered)!=list(range(1,len(part[0]['pages'])+1)):raise ValueError('Диапазоны содержат пропуск или повтор страниц.')
                chosen=[r for r in records if r.get('enabled',True)]
                if not chosen:messagebox.showinfo('Паспорта','Отметьте хотя бы один документ.');return
                missing=[r for r in chosen if not r['date'] or not r['number']]
                if missing and not messagebox.askyesno('Неполные реквизиты',f'У {len(missing)} документов нет номера или полной даты. Вы проверили оригиналы и хотите сохранить именно так?',parent=win):return
                output=destination or filedialog.askdirectory(parent=win,title='Куда сохранить папку «Паспорта»?',initialdir=str(app.project or app.catalog_dir))
                if not output:return
                saving[0]=True
                status.set('Сохраняем документы… Можно свернуть окно.')
                # Keep source temporary files alive until the background save
                # finishes. Avoid closing/restarting the job while it writes.
                win.protocol('WM_DELETE_WINDOW',lambda:status.set('Дождитесь завершения сохранения документов.'))
                results=queue.Queue()
                snapshot=[dict(record,rotations=dict(record.get('rotations',{}))) for record in chosen]
                def save():
                    try:results.put(('ready',save_records(snapshot,output)))
                    except Exception as exc:results.put(('error',str(exc)))
                threading.Thread(target=save,daemon=True).start()
                def saved():
                    if not win.winfo_exists():return
                    try:kind,data=results.get_nowait()
                    except queue.Empty:win.after(50,saved);return
                    saving[0]=False
                    win.protocol('WM_DELETE_WINDOW',lambda:(win.destroy(),tmp.cleanup()))
                    if kind=='error':
                        status.set('Сохранение не завершено. Можно повторить.')
                        messagebox.showerror('Сохранение',data,parent=win);return
                    folder,meta=data
                    app.store_passports(folder,meta)
                    messagebox.showinfo('Готово',f'Сохранено документов: {len(meta)}\n{folder}',parent=win)
                    win.destroy();tmp.cleanup()
                win.after(50,saved)
            except Exception as exc:messagebox.showerror('Сохранение',str(exc))
        actions=nav
        for key,label,fn in [('cut','Разделить перед текущей страницей',split),('link','Объединить со следующим документом',merge),('save','Сохранить отмеченные документы отдельными PDF',finish)]:
            app.icon_button(actions,key,label,fn)
        load(0);refresh();app.paint(win)
    win.after(100,poll)
