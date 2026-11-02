"""Inventory, page accounting and publishing a selected set of project documents."""
from dataclasses import dataclass
from pathlib import Path
from io import BytesIO
import datetime
import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import tempfile
import time
from pypdf import PdfReader,PdfWriter
from openpyxl import load_workbook
from workspace_preview import Session,ROOT
from app_paths import APP_DIR

OFFICE={'.xlsx','.xls','.docx','.doc'}
def nat(text):
    return tuple((0,int(s)) if s.isdigit() else (1,s.casefold()) for s in re.split(r'(\d+)',str(text)))
def safe(text):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',str(text)).strip(' .')[:150] or 'Документ'
def norm(text):
    return re.sub(r'[^\w]','',str(text or '').casefold().replace('×','х').replace('x','х'))
def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
@dataclass
class Item:
    path:Path
    section:str
    role:str
    parent:Path|None=None
    number:str=''
    date:str=''
    title:str=''
    edited:bool=False
    duplicate_group:str=''
    order:int|None=None
    @property
    def key(self):return self.section,self.path,self.parent

def book_rows(p):
    book=load_workbook(p,read_only=True,data_only=True)
    try:return list(book.active.values)
    finally:book.close()
def date_str(v):
    if isinstance(v,(datetime.datetime,datetime.date)):return v.strftime('%d.%m.%Y')
    text=str(v or '')
    m=re.search(r'(\d{1,2})["»]?\s+([а-я]+)\s+(\d{4})',text,re.I)
    months='января февраля марта апреля мая июня июля августа сентября октября ноября декабря'.split()
    if m and m[2].lower() in months:return f'{int(m[1]):02}.{months.index(m[2].lower())+1:02}.{m[3]}'
    return text
def inventory(project,catalog):
    base=project/'Документы';meta=json.loads((project/'project.json').read_text('utf-8'))
    edited=set(meta.get('edited',[]));files=sorted((p for p in base.rglob('*') if p.is_file() and not p.name.startswith('~$') and 'шаблоны' not in {x.casefold() for x in p.relative_to(base).parts[:-1]}),key=nat)
    origin=Path(meta['source']) if meta.get('source') else ROOT.parent/project.name
    def revised(path):
        if str(path.relative_to(project)) in edited:return True
        external=origin/path.relative_to(base) if origin.is_dir() else origin
        if not external.is_file() or external.suffix.lower()!=path.suffix.lower() or external.resolve()==path.resolve():return False
        if digest(external)==digest(path):return False
        try:
            if path.suffix.lower()=='.xlsx':
                def values(f):
                    w=load_workbook(f,read_only=True,data_only=False)
                    try:return [[tuple((c.coordinate,str(c.value)) for row in sh for c in row if c.value is not None)] for sh in w]
                    finally:w.close()
                return values(path)!=values(external)
            if path.suffix.lower()=='.docx':
                import zipfile
                from lxml import etree
                def text(f):
                    with zipfile.ZipFile(f) as z:return etree.fromstring(z.read('word/document.xml')).xpath('//*[local-name()="t"]/text()')
                return text(path)!=text(external)
        except (OSError,ValueError,KeyError):return False
        return True
    result=[];regs=[];passports=[];byfolder={};reference={}
    for p in files:
        f=p.stem.casefold();suffix=p.suffix.lower()
        if suffix not in OFFICE|{'.pdf','.jpg','.jpeg'}:continue
        parts=p.relative_to(base).parts
        section=next((s for s in parts[:-1] if re.search(r'(?:^|\W)(?:КЖ|КМ|АР|АС|ОВ|ВК|ЭОМ)(?:$|\W)',s,re.I)),parts[0] if len(parts)>1 and not any(x in parts[0].casefold() for x in ('паспорт','сертификат')) else 'Общее')
        if 'титул' in f:role='Титул'
        elif f.startswith('реестр') and not any(x in f for x in (' к ','качества','приложен')):role='Реестр'
        elif f.startswith(('аоср','аоок')):role='Акт'
        elif 'реестр' in f or 'приложен' in f:role='Приложение'
        elif suffix in OFFICE:role='Документ'
        elif re.match(r'^(ис(?:\W|$)|исполнительн)',f):role='Схема'
        elif any('паспорт' in x.casefold() for x in parts) or re.search('сертификат|паспорт|декларац|отказное|протокол|письмо|^пк ',f):role='Паспорт'
        elif len(parts)>2:role='Паспорт'
        else:continue  # project drawings are reference material
        wordplan=None
        if suffix in ('.doc','.docx'):
            from project_analysis import saved_word_plan,cached_word_plan
            wordplan=saved_word_plan(p) or cached_word_plan(p)
            if wordplan:role={'act':'Акт','quality':'Приложение','registry':'Реестр','title':'Титул'}.get(wordplan['kind'],role)
        it=Item(p,section,role,title=p.stem,edited=revised(p))
        if wordplan:
            values={k:v['value'] for k,v in wordplan['fields'].items()}
            it.number=values.get('number',values.get('qualityNumber',''));it.date=values.get('actDate',values.get('refDate',''))
            if values.get('work'):it.title=values['work']
        result.append(it)
        if role=='Акт':
            byfolder.setdefault(p.parent,[]).append(it)
            if suffix=='.xlsx':
                rows=book_rows(p)
                if len(rows)>=24 and len(rows[23])>=12:
                    it.number=str(rows[23][1] or '');it.date=date_str(rows[23][11])
                    work=next((str(r[7]) for r in rows if len(r)>7 and 'освидетельствованию предъявлены' in ' '.join(str(r[1] or '').lower().split()) and r[7]),'')
                    if work:it.title=('АООК ' if f.startswith('аоок') else 'АОСР ')+work
        elif role=='Приложение' and suffix=='.xlsx':regs.append(it)
        elif role=='Паспорт':passports.append(it)
    for it in result:
        if it.role in ('Схема','Приложение','Паспорт'):
            owners=byfolder.get(it.path.parent,[])
            if len(owners)==1:it.parent=owners[0].path
    for r in regs:
        data=book_rows(r.path)
        if len(data)>8:
            head=' '.join(str(v) for v in data[1] if v);date=re.search(r'\d{2}\.\d{2}\.\d{4}',head)
            descr=' '.join(str(v) for v in data[5] if v).strip()
            match=re.search(r'№\s*(\S+)\s*$',descr)
            if date:r.date=date[0]
            if match:r.number='№'+match[1];r.title=descr[:match.start()].strip()
        if len(data)>8 and 'материал' in str(data[7][1]).casefold():
            for row in data[8:]:
                if len(row)<6 or not isinstance(row[0],(int,float)):continue
                for key in [norm(row[1]),norm(row[3])]:
                    if key:reference.setdefault(key,[]).append((r, row))
    cat=json.loads(catalog.read_text('utf-8')) if catalog.exists() else []
    for p in passports:
        match=next((m for m in cat if Path(m['file']).resolve()==p.path.resolve()),None)
        refs=reference.get(norm(p.path.stem),[])
        if match:
            p.number=match['number'];p.date=match['date'];p.title=match['type'];refs=reference.get(norm(p.number),refs)
        # One physical passport can be referenced by several attachment tables.
        parents=set()
        for reg,row in refs:
            if reg.section!=p.section and p.section!='Общее' and not match:continue
            if not p.number:p.number=str(row[3] or '');p.date=date_str(row[4]);p.title=str(row[2] or p.title)
            if reg.parent:parents.add((reg.section,reg.parent))
        if parents:
            from dataclasses import replace
            result.remove(p)
            for sec,owner in sorted(parents,key=lambda pair:nat(pair[1])):result.append(replace(p,section=sec,parent=owner))
    # Restore explicit links chosen earlier; they can span sections.
    from dataclasses import replace
    for record in meta.get('package_links',[]):
        path=base/record['file'];owner=base/record['act']
        original=next((i for i in result if i.path==path),None);act=next((i for i in result if i.path==owner and i.role=='Акт'),None)
        if not original or not act or any(i.path==path and i.parent==owner for i in result):continue
        if original.parent:result.append(replace(original,parent=owner,section=act.section))
        else:original.parent=owner;original.section=act.section
    known={}
    for it in result:
        if it.role=='Паспорт' and it.number:known[digest(it.path)]=(it.number,it.date,it.title)
    if known:
        for it in result:
            if it.role=='Паспорт' and not it.number:
                info=known.get(digest(it.path))
                if info:it.number,it.date,it.title=info
    for it in result:it.duplicate_group=meta.get('confirmed_duplicates',{}).get(str(it.path.relative_to(base)),'')
    return result

def ordered(items,drop):
    seen={};remaining=[]
    for item in items:
        if drop and item.role=='Паспорт':
            key=item.duplicate_group or digest(item.path)
            if key in seen:continue
            seen[key]=item
        remaining.append(item)
    ranks={i.path:i.order for i in remaining if i.role=='Акт'}
    return sorted(remaining,key=lambda i:({'Титул':0,'Реестр':1,'Паспорт':3}.get(i.role,2),nat(i.section),ranks.get(i.parent) if ranks.get(i.parent) is not None else i.order if i.role=='Акт' and i.order is not None else 100000, nat(i.parent or i.path),0 if i.role=='Акт' else 1,i.order if i.order is not None else 100000,nat(i.path)))

def spans(items,counts,section_numbers):
    offsets={};rows=[]
    for it in items:
        if it.role in ('Титул','Реестр'):continue
        k=it.section if section_numbers else '';first=offsets.get(k,0)+1;count=counts[it.path];end=first+count-1;offsets[k]=end
        rows.append(dict(item=it,count=count,span=str(first) if first==end else f'{first}-{end}',title=it.title,number=it.number,date=it.date))
    return rows

def render(path,temp,cache):
    if path in cache:return cache[path]
    if path.suffix.lower()=='.pdf':return path.read_bytes()
    if path.suffix.lower() in ('.jpg','.jpeg'):
        from PIL import Image
        buf=BytesIO()
        with Image.open(path) as im:im.convert('RGB').save(buf,'PDF')
        return buf.getvalue()
    work=Path(tempfile.mkdtemp(dir=temp))/path.name;shutil.copy2(path,work)
    events=queue.Queue();worker=Session(work,events,prepared=True)
    try:
        while True:
            _,kind,value=events.get(timeout=180)
            if kind=='error':raise ValueError(f'{path.name}: {value}')
            if kind=='pdf':return value[1]
    finally:worker.tasks.put(None);worker.thread.join(30)

def set_print_width(path):
    # Change only the page setup in the exported OOXML package.
    import zipfile
    from lxml import etree
    temp=path.with_suffix('.tmp');ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    with zipfile.ZipFile(path) as src,zipfile.ZipFile(temp,'w') as dst:
        for info in src.infolist():
            data=src.read(info)
            if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',info.filename):
                sheet=etree.fromstring(data);pr=sheet.find(ns+'sheetPr')
                if pr is None:pr=etree.Element(ns+'sheetPr');sheet.insert(0,pr)
                props=pr.find(ns+'pageSetUpPr')
                if props is None:props=etree.SubElement(pr,ns+'pageSetUpPr')
                props.set('fitToPage','1');setup=sheet.find(ns+'pageSetup')
                if setup is None:
                    setup=etree.Element(ns+'pageSetup')
                    after=sheet.find(ns+'pageMargins')
                    if after is not None:after.addnext(setup)
                    else:sheet.append(setup)
                setup.attrib.pop('scale',None);setup.set('fitToWidth','1');setup.set('fitToHeight','0')
                data=etree.tostring(sheet,encoding='UTF-8',xml_declaration=True,standalone=True)
            dst.writestr(info,data)
    temp.replace(path)

def make_registry(source,out,pdf,rows,address=''):
    from workspace_preview import ROOT
    shutil.copy2(source,out)
    payload=pdf.with_suffix('.json');payload.write_text(json.dumps({'entries':[{k:v for k,v in r.items() if k!='item'} for r in rows],'address':address},ensure_ascii=False),'utf-8')
    try:
        run=subprocess.run(['powershell.exe','-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',str(APP_DIR/'MakeRegistry.ps1'),'-File',str(out),'-Data',str(payload),'-Pdf',str(pdf)],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
        if run.returncode:raise ValueError(run.stderr.decode('oem',errors='replace'))
        set_print_width(out)
    finally:payload.unlink(missing_ok=True)

def publish(project,selected,target,cache,options,progress):
    target=Path(target);target.mkdir(parents=True,exist_ok=True)
    if target.resolve().is_relative_to(project.resolve()):raise ValueError('Выберите папку выгрузки вне проекта.')
    name=project.name
    if options['version']:
        original=name;n=1
        while (target/name).exists() or (target/(name+' для печати')).exists():
            n+=1;name=f'{original} — версия {n}'
    titles=[i for i in selected if i.role=='Титул'];registers=[i for i in selected if i.role=='Реестр']
    if len(titles)>1 or len(registers)>1:raise ValueError('Для комплекта выберите один титул и один общий реестр.')
    sources=ordered(selected,False)
    with tempfile.TemporaryDirectory(dir=target,prefix='.БюроИД-') as stage:
        stage=Path(stage);work=stage/'temp';work.mkdir()
        edits=stage/name;prints=stage/(name+' для печати');edits.mkdir();prints.mkdir()
        counts={};rendered={}
        for i in sources:
            if i.path in rendered or (i.role=='Реестр' and options['rebuild']):continue
            progress('Подготовка: '+i.path.name)
            if i.path.suffix.lower()=='.pdf':pdf=i.path
            else:
                cache_dir=project/'Кэш PDF';cache_dir.mkdir(exist_ok=True)
                pdf=cache_dir/(digest(i.path)+'-print-v1.pdf')
                if i.path in cache or not pdf.exists():
                    data=render(i.path,work,cache)
                    with tempfile.NamedTemporaryFile(dir=cache_dir,delete=False) as f:f.write(data)
                    Path(f.name).replace(pdf)
            rendered[i.path]=pdf
            counts[i.path]=len(PdfReader(pdf).pages)
        for p in set(i.path for i in sources if i.role!='Реестр' or not options['rebuild']):
            rel=p.relative_to(project/'Документы');dest=edits/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
            if dest.suffix.lower()=='.xlsx' and any(i.path==p and i.role in ('Реестр','Приложение') for i in sources):
                set_print_width(dest)
        def build_one(group,pdir,stem,overall):
            pdir.mkdir(parents=True,exist_ok=True)
            group=ordered(group,options['dedup'])
            rows=spans(group,counts,options['section_numbers']);rowiter=iter(rows)
            regpdf=None
            if registers and not options['rebuild']:
                existing=[]
                for raw in book_rows(registers[0].path)[7:]:
                    if len(raw)<6 or not isinstance(raw[0],(int,float)) or not raw[1] or str(raw[1])=='Всего позиций':continue
                    existing.append(raw)
                if len(existing)!=len(rows) or any(str(old[5])!=row['span'] or int(old[4] or 0)!=row['count'] or
                     (norm(old[2])!=norm(row['number']) if old[2] and row['number'] else norm(old[1])!=norm(row['title']))
                     for old,row in zip(existing,rows)):
                    raise ValueError('Выбранный состав отличается от сохранённого реестра. Включите «Пересоставить реестр».')

            if registers and options['rebuild']:
                excel=(edits/(registers[0].path.relative_to(project/'Документы') if registers[0].path.is_relative_to(project/'Документы') else Path('Реестр.xlsx'))) if overall else edits/'Раздельные комплекты'/stem/'Реестр.xlsx'
                excel.parent.mkdir(parents=True,exist_ok=True);regpdf=work/(safe(stem)+'-registry.pdf')
                progress('Пересоставление реестра: '+stem);make_registry(registers[0].path,excel,regpdf,rows)
            joined=options['combined'] if overall else options['separate']
            writer=PdfWriter() if joined else None
            for it in group:
                doc=regpdf if regpdf is not None and it.role=='Реестр' else rendered[it.path]
                if it.role in ('Реестр','Титул'):dest=pdir/(safe(it.role)+'.pdf')
                else:
                    row=next(rowiter);sub=pdir/safe(it.section)
                    if it.role=='Паспорт':sub=sub/'Паспорта'
                    elif it.parent:sub=sub/safe(it.parent.stem)
                    elif it.role=='Акт':sub=sub/safe(it.path.stem)
                    dest=sub/(row['span']+'. '+safe(it.path.stem)+'.pdf')
                if options.get('individual',True):
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    if dest.exists():raise ValueError('Совпали имена печатных файлов: '+str(dest.name))
                    shutil.copy2(doc,dest)
                if writer is not None:writer.append(str(doc))
            if group and writer is not None:
                with (pdir/(safe(stem)+' — комплект.pdf')).open('wb') as out:writer.write(out)
            if writer is not None:writer.close()
        if options['combined'] or options.get('individual',True):build_one(sources,prints,name,True)
        if options['separate']:
            sections=sorted({i.section for i in sources if i.role not in ('Титул','Реестр')},key=nat)
            for sec in sections:
                group=[i for i in sources if i.section==sec or i.role in ('Титул','Реестр')]
                build_one(group,prints/'По разделам'/safe(sec),sec,False)
        for directory in (edits,prints):
            (directory/'.БюроИД.json').write_text(json.dumps({'project':str(project.resolve()),'files':[str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()]},ensure_ascii=False),'utf-8')
        previous=[];published=[]
        try:
            for directory in (edits,prints):
                dest=target/directory.name
                if dest.exists():
                    marker=dest/'.БюроИД.json'
                    if not marker.is_file():raise ValueError(f'Папка {dest.name} не является выгрузкой программы. Выберите новую версию.')
                    manifest=json.loads(marker.read_text('utf-8'))
                    if manifest['project']!=str(project.resolve()):raise ValueError('В этой папке выгрузка другого проекта.')
                    managed=set(manifest['files'])|{marker.name}
                    for f in dest.rglob('*'):
                        if f.is_file() and str(f.relative_to(dest)) not in managed:
                            keep=directory/f.relative_to(dest)
                            if keep.exists():raise ValueError('Конфликт с пользовательским файлом: '+str(f))
                            keep.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,keep)
                    backup=stage/('old-'+dest.name);os.replace(dest,backup);previous.append((backup,dest))
                os.replace(directory,dest);published.append((directory,dest))
        except Exception:
            for directory,dest in reversed(published):os.replace(dest,directory)
            for backup,dest in reversed(previous):os.replace(backup,dest)
            raise
    return target/(name+' для печати')

def measure_selection(project,items,cache,options,cancel,progress):
    counts={}
    unique=list(dict.fromkeys(it.path for it in items))
    with tempfile.TemporaryDirectory(prefix='bureau-count-') as tmp:
        tmp=Path(tmp)
        cachedir=project/'Кэш PDF';cachedir.mkdir(exist_ok=True)
        for ix,path in enumerate(unique,1):
            if cancel.is_set():return None
            if any(it.path==path and it.role=='Реестр' for it in items) and options['rebuild']:continue
            progress(f'Подсчёт страниц · {ix} / {len(unique)}')
            if path in cache:data=cache[path]
            elif path.suffix.lower()=='.pdf':data=path.read_bytes()
            else:
                out=cachedir/(digest(path)+'-print-v1.pdf')
                if not out.exists():
                    data=render(path,tmp,cache);temp=out.with_suffix('.count.tmp');temp.write_bytes(data);temp.replace(out)
                data=out.read_bytes()
            counts[path]=len(PdfReader(BytesIO(data)).pages)
        def group_total(group,stem):
            group=ordered(group,options['dedup']);rows=spans(group,counts,options['section_numbers'])
            pages=sum(row['count'] for row in rows)
            for item in group:
                if item.role=='Титул':pages+=counts[item.path]
                elif item.role=='Реестр':
                    if options['rebuild']:
                        file=tmp/(safe(stem)+'.xlsx');pdf=tmp/(safe(stem)+'.pdf')
                        make_registry(item.path,file,pdf,rows);pages+=len(PdfReader(BytesIO(pdf.read_bytes())).pages)
                    else:pages+=counts[item.path]
            return len(group),pages
        primary=group_total(items,'Общий') if items else (0,0)
        separate=None
        if options['separate']:
            separate=0
            for section in sorted({it.section for it in items if it.role not in ('Титул','Реестр')},key=nat):
                if cancel.is_set():return None
                group=[it for it in items if it.section==section or it.role in ('Титул','Реестр')]
                separate+=group_total(group,section)[1]
        return primary,separate

class PackageDialog:
    def __init__(self,app):
        import tkinter as tk
        from tkinter import ttk,messagebox,filedialog
        import threading
        self.app=app;self.window=tk.Toplevel(app.root);w=self.window;w.title('Сборка исполнительной документации');w.geometry('940x680');w.minsize(900,500)
        app.window_ribbon(w)
        self.items=inventory(app.project,app.catalog_dir/'Документы качества.json')
        if not self.items:w.destroy();messagebox.showinfo('Сборка','В проекте нет документов для выгрузки.');return
        for rank,it in enumerate(ordered(self.items,False)):it.order=rank
        self.checked=set(range(len(self.items)))
        # Prefer the project-level title and register. Other section-specific candidates remain selectable.
        for role in ('Титул','Реестр'):
            candidates=sorted((i for i,it in enumerate(self.items) if it.role==role),key=lambda i:len(self.items[i].path.parts))
            for i in candidates[1:]:self.checked.discard(i)
        self.group_ids={};self.leaves={};self.busy=False
        ttk.Label(w,text='Комплект для печати',font=('Segoe UI',15,'bold'),padding=8).pack(anchor='w')
        options=ttk.Frame(w);options.pack(fill='x',padx=8)
        self.vars={k:tk.BooleanVar(value=v) for k,v in [('combined',True),('separate',False),('individual',True),('section_numbers',True),('dedup',False),('rebuild',True),('version',True)]}
        for k,title in [('combined','Общий файл ИД'),('separate','Общие файлы по разделам'),('individual','Отдельные PDF-документы'),('section_numbers','Нумерация с 1 по разделам'),('dedup','Убирать дубликаты паспортов'),('rebuild','Пересоставить реестр по выбранным документам')]:
            cb=ttk.Checkbutton(options,text=title,variable=self.vars[k])
            ix=list(self.vars).index(k);cb.grid(row=ix//3,column=ix%3,sticky='w',padx=3,pady=4)
            from hints import tooltip
            tooltip(cb,{'combined':'Один PDF: титул, реестр, акты с приложениями, затем паспорта.','separate':'Отдельный комплект PDF для каждого раздела.','individual':'Сохранить каждый выбранный документ отдельным PDF.','section_numbers':'Начинать нумерацию страниц с единицы в каждом разделе.','dedup':'Оставить в печатном комплекте один экземпляр одинаковых паспортов.','rebuild':'Обновить список и номера страниц: включить только отмеченные файлы в порядке их печати.'}[k])
            if k=='section_numbers':cb.configure(command=lambda:self.vars['dedup'].set(not self.vars['section_numbers'].get()))
        row=ttk.Frame(w);row.pack(fill='x',padx=8,pady=4)
        for title,fn in [('Отметить все',lambda:self.select(True)),('Снять все',lambda:self.select(False)),('Выше',lambda:self.move(-1)),('Ниже',lambda:self.move(1)),('Связать с актом…',self.link)]:
            key={'Отметить все':'checkall','Снять все':'uncheckall','Выше':'up','Ниже':'down','Связать с актом…':'link'}[title]
            app.icon_button(row,key,{'Выше':'Предыдущий файл во всём списке','Ниже':'Следующий файл во всём списке'}.get(title,title),fn)
        self.calc_button=app.icon_button(row,'calculate',lambda:'Рассчитать страницы и примерное время'+('\n'+self.stats_error if getattr(self,'stats_error','') else ''),self.start_stats)
        ttk.Label(row,text='★ изменён в проекте').pack(side='right')
        area=ttk.Frame(w);area.pack(fill='both',expand=True,padx=8)
        app.style.configure('Package.Treeview',rowheight=25)
        app.style.map('Package.Treeview',foreground=[('selected','black')],background=[('selected','#e8ddd3')])
        self.tree=ttk.Treeview(area,columns=('role',),show='tree headings',selectmode='browse',style='Package.Treeview')
        self.tree.bind('<Up>',lambda e:(self.move(-1),'break')[1]);self.tree.bind('<Down>',lambda e:(self.move(1),'break')[1])
        from keyboard_navigation import install as arrow_navigation
        arrow_navigation(w,self.move)
        self.tree.heading('#0',text='Раздел / акт / связанные документы');self.tree.heading('role',text='Тип документа')
        self.tree.column('#0',width=650,minwidth=480);self.tree.column('role',width=105,stretch=False)
        sy=ttk.Scrollbar(area,command=self.tree.yview);sx=ttk.Scrollbar(area,orient='horizontal',command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set,xscrollcommand=sx.set);sx.pack(side='bottom',fill='x');sy.pack(side='right',fill='y');self.tree.pack(fill='both',expand=True)
        self.tree.tag_configure('edit',foreground='#ae633b')
        self.tree.bind('<Button-1>',self.click);self.tree.bind('<space>',lambda e:self.toggle(self.tree.focus()))
        self.totals_text=tk.StringVar(value='Для подсчёта страниц нажмите иконку «Рассчитать».')
        self.stats_epoch=0;self.stats_running=False;self.stats_timer=None
        self.build()
        ttk.Label(w,textvariable=self.totals_text,padding=(8,4),wraplength=850).pack(fill='x')
        foot=ttk.Frame(w);foot.pack(fill='x',padx=8,pady=8)
        ttk.Radiobutton(foot,text='Новая версия',value=True,variable=self.vars['version']).pack(side='left')
        ttk.Radiobutton(foot,text='Обновить выгрузку с заменой',value=False,variable=self.vars['version']).pack(side='left')
        self.status=tk.StringVar(value='Титул → реестр → акты и приложения → паспорта')
        ttk.Label(w,textvariable=self.status,padding=6).pack(anchor='w')
        self.go=ttk.Button(foot,text='Выгрузить',image=app.icon('assemble'),compound='left',style='Compact.TButton',command=self.run);self.go.pack(side='right');__import__('hints').hover_icon(self.go,app,'assemble');__import__('hints').tooltip(self.go,'Собрать и выгрузить выбранный комплект')
        app.paint(w)
        from tree_hover import install
        self.hide_hover=install(self.tree)
        for var in self.vars.values():var.trace_add('write',lambda *args:self.queue_stats())
        w.protocol('WM_DELETE_WINDOW',self.close_dialog)
    def close_dialog(self):
        if self.busy:return
        if hasattr(self,'stats_cancel'):self.stats_cancel.set()
        if self.stats_timer:self.window.after_cancel(self.stats_timer)
        self.window.destroy()
    def queue_stats(self):
        if not hasattr(self,'totals_text') or not self.window.winfo_exists():return
        self.stats_epoch+=1
        if self.stats_running:self.stats_cancel.set()
        selected=[self.items[i] for i in self.checked]
        self.totals_text.set(f'Выбрано документов: {len(selected)} · Для страниц нажмите «Рассчитать».')
    def start_stats(self):
        import threading
        self.stats_timer=None
        if self.stats_running:return
        epoch=self.stats_epoch;selected=[self.items[i] for i in sorted(self.checked)]
        opts={k:v.get() for k,v in self.vars.items()}
        if not selected:self.totals_text.set('Документов: 0 · Страниц: 0');return
        self.stats_running=True;self.stats_cancel=threading.Event();events=queue.Queue();self.stats_error=''
        self.stats_started=time.monotonic()
        total=len(set(it.path for it in selected))
        self.stats_estimate=max(2,sum(0.15 if it.path.suffix.lower()=='.pdf' else 3.0 for it in {i.path:i for i in selected}.values()))
        if opts['rebuild']:self.stats_estimate+=3
        self.totals_text.set(f'Расчёт страниц · Примерно {self.stats_estimate:.0f} сек.')
        state={'progress':'Подготовка','completed':0}

        cache={s.copy:data for s,data in self.app.latest.items() if self.app.saved_rev.get(s,-1)==self.app.revisions.get(s)}
        def work():
            try:events.put(('done',measure_selection(self.app.project,selected,cache,opts,self.stats_cancel,lambda x:events.put(('status',x)))))
            except Exception as exc:events.put(('error',str(exc)))
        def poll():
            if not self.window.winfo_exists():self.stats_cancel.set();return
            while not events.empty():
                kind,data=events.get()
                if kind=='status' and epoch==self.stats_epoch:
                    state['progress']=data
                    match=re.search(r'(\d+) / (\d+)',data)
                    if match:state['completed']=max(0,int(match[1])-1)
                elif kind!='status':
                    self.stats_running=False
                    if epoch!=self.stats_epoch:return
                    if kind=='error':
                        self.stats_error=data;self.totals_text.set('Ошибка расчёта. Подробности — в подсказке кнопки «Рассчитать».')
                        self.status.set('Проверьте указанный документ и повторите расчёт.')
                    elif data is not None:
                        (docs,pages),separate=data
                        text=f'Документов: {docs} · Страниц выбранного комплекта: {pages}'
                        if separate is not None:text+=f' · В файлах по разделам: {separate} стр.'
                        self.totals_text.set(text)
                    return
            if epoch==self.stats_epoch:
                elapsed=time.monotonic()-self.stats_started
                completed=state['completed']
                estimate=self.stats_estimate if not completed else max(self.stats_estimate,elapsed/max(1,completed)*total)
                remaining=max(1,estimate-elapsed)
                self.totals_text.set(f"{state['progress']} · Осталось примерно {remaining:.0f} сек. · Прошло {elapsed:.0f} сек.")
            self.window.after(120,poll)
        threading.Thread(target=work,daemon=True).start();poll()
    def build(self):
        tree=self.tree;tree.delete(*tree.get_children());self.group_ids.clear();self.leaves.clear()
        sections={};acts={}
        for i,it in enumerate(self.items):
            if it.role=='Акт':acts[(it.section,it.path)]=i
        def group(key):
            if key not in sections:
                gid=tree.insert('','end',open=True);sections[key]=gid;self.group_ids[gid]=(key,set())
            return sections[key]
        def add(i):
            if i in self.leaves:return self.leaves[i]
            it=self.items[i];gid=group('Общие документы' if it.role in ('Титул','Реестр') else it.section)
            owner=acts.get((it.section,it.parent))
            parent=add(owner) if owner is not None else gid
            node=tree.insert(parent,'end',iid='f'+str(i),open=False,values=(it.role,),tags=('edit',) if it.edited else ())
            self.leaves[i]=node;self.group_ids[gid][1].add(i);return node
        for i in sorted(range(len(self.items)),key=lambda i:self.items[i].order if self.items[i].order is not None else 100000):add(i)
        self.refresh()
    def refresh(self):
        if hasattr(self,'hide_hover'):self.hide_hover()
        for i,node in self.leaves.items():
            it=self.items[i];txt=('☑ ' if i in self.checked else '☐ ')+('★ ' if it.edited else '')+it.path.name
            self.tree.item(node,text=txt)
        for node,(name,ids) in self.group_ids.items():
            count=len(ids & self.checked);self.tree.item(node,text=('☑ ' if count==len(ids) else '◩ ' if count else '☐ ')+name)
        self.queue_stats()
    def select(self,all_):
        self.checked=set(range(len(self.items))) if all_ else set()
        self.refresh()
    def click(self,e):
        self.tree.focus_set()
        row=self.tree.identify_row(e.y)
        if row and 'indicator' not in self.tree.identify_element(e.x,e.y):
            self.tree.selection_set(row);self.tree.focus(row);self.toggle(row);return 'break'
    def toggle(self,node):
        if not node:return
        if node in self.group_ids:ids=self.group_ids[node][1];turn_on=not ids<=self.checked
        else:
            idx=int(node[1:]);it=self.items[idx];turn_on=idx not in self.checked;ids={idx}
            if it.role=='Акт':ids.update(i for i,x in enumerate(self.items) if x.parent==it.path and x.section==it.section)
        if turn_on:self.checked.update(ids)
        else:self.checked.difference_update(ids)
        self.refresh()
    def move(self,step):
        files=[]
        def visit(parent=''):
            for node in self.tree.get_children(parent):
                if node.startswith('f'):files.append(node)
                visit(node)
        visit()
        if not files:return
        current=self.tree.focus()
        index=files.index(current)+step if current in files else (0 if step>0 else len(files)-1)
        index=max(0,min(len(files)-1,index));node=files[index]
        self.tree.selection_set(node);self.tree.focus(node);self.tree.see(node)
    def link(self):
        from tkinter import ttk,messagebox,Toplevel
        node=self.tree.focus()
        if not node.startswith('f'):return
        i=int(node[1:]);it=self.items[i]
        if it.role not in ('Паспорт','Схема','Приложение','Документ'):
            messagebox.showinfo('Связь','Выберите приложение, схему или паспорт.');return
        win=Toplevel(self.window);win.title('Связать документ с актом')
        acts=[x for x in self.items if x.role=='Акт']
        if not acts:win.destroy();return
        sel=ttk.Combobox(win,values=[x.section+' · '+x.path.stem for x in acts],state='readonly',width=65);sel.pack(padx=8,pady=8);sel.current(0)
        def choose():
            owner=acts[sel.current()]
            from dataclasses import replace
            if it.parent and it.parent!=owner.path:
                if not any(x.path==it.path and x.parent==owner.path for x in self.items):self.items.append(replace(it,section=owner.section,parent=owner.path));self.checked.add(len(self.items)-1)
            else:it.parent=owner.path;it.section=owner.section
            manifest=self.app.project/'project.json';data=json.loads(manifest.read_text('utf-8'))
            base=self.app.project/'Документы';record=dict(file=str(it.path.relative_to(base)),act=str(owner.path.relative_to(base)))
            if record not in data.setdefault('package_links',[]):data['package_links'].append(record)
            temp=manifest.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf-8');temp.replace(manifest)
            self.build();win.destroy()
        row=ttk.Frame(win);row.pack(fill='x',padx=8,pady=6)
        button=ttk.Button(row,text='Применить',image=self.app.icon('link'),compound='left',style='Compact.TButton',command=choose);button.pack(side='right');__import__('hints').hover_icon(button,self.app,'link');__import__('hints').tooltip(button,'Связать выбранный документ с этим актом');self.app.paint(win)
    def run(self):
        import threading
        from tkinter import messagebox,filedialog
        if self.busy:return
        if self.stats_running:self.status.set('Дождитесь завершения подсчёта страниц.');return
        options={k:v.get() for k,v in self.vars.items()};selected=[self.items[i] for i in sorted(self.checked)]
        if not selected or not(options['combined'] or options['separate'] or options['individual']):
            messagebox.showinfo('Сборка','Выберите документы и способ сборки.');return
        from package_checks import show as check_package
        if check_package(self.app,selected):return
        for it in selected:
            s=self.app.sessions.get(it.path)
            if s and self.app.saved_rev.get(s,-1)!=self.app.revisions[s]:
                messagebox.showinfo('Сборка','Дождитесь сохранения документа: '+it.path.name);return
        if options['rebuild'] and not any(i.role=='Реестр' for i in selected):
            source=next((self.app.catalog_dir/'Шаблоны').rglob('Шаблон Реестр.xlsx'),None)
            if not source or not messagebox.askyesno('Реестр','Общий реестр не выбран. Сформировать его из библиотечного шаблона?'):return
            selected.append(Item(source,'Общее','Реестр',title='Реестр'))
        target=filedialog.askdirectory(parent=self.window,title='Родительская папка для выгрузки')
        if not target:return
        project=self.app.project
        cache={}
        cache.update({s.copy:data for s,data in self.app.latest.items() if self.app.saved_rev.get(s,-1)==self.app.revisions.get(s)})
        events=queue.Queue();self.busy=True;self.go.state(['disabled'])
        self.window.protocol('WM_DELETE_WINDOW',lambda:messagebox.showinfo('Сборка','Идёт сохранение комплекта.'))
        def worker():
            try:events.put(('done',publish(project,selected,target,cache,options,lambda msg:events.put(('status',msg)))))
            except Exception as e:events.put(('error',str(e)))
        def poll():
            while not events.empty():
                kind,data=events.get()
                if kind=='status':self.status.set(data)
                elif kind=='error':
                    self.busy=False;self.go.state(['!disabled']);self.window.protocol('WM_DELETE_WINDOW',self.window.destroy);messagebox.showerror('Сборка',data);return
                else:self.window.destroy();messagebox.showinfo('Выгрузка завершена',str(data));return
            if epoch==self.stats_epoch:
                elapsed=time.monotonic()-self.stats_started
                completed=state['completed']
                estimate=self.stats_estimate if not completed else max(self.stats_estimate,elapsed/max(1,completed)*total)
                remaining=max(1,estimate-elapsed)
                self.totals_text.set(f"{state['progress']} · Осталось примерно {remaining:.0f} сек. · Прошло {elapsed:.0f} сек.")
            self.window.after(120,poll)
        threading.Thread(target=worker,daemon=True).start();poll()


