"""Project-specific quality documents and their explicit catalogue choices."""
from pathlib import Path
import hashlib,json,re
from tkinter import ttk
from passports import inspect
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def reference_text(text):
    return re.sub(r'(\b\d{2}\.\d{2}\.\d{4})(?!\d)(?!\s*г\.?)',r'\1 г.',text)
def record_text(record):
    number=record.get('number','');date=record.get('date','');material=record.get('material','')
    if not number and not date and material:return material
    return reference_text(record['type']+(' №'+number if number else ' б/н')+(' от '+date if date else ''))
class QualityLibrary:
    def quality_records(self):
        file=self.catalog_dir/'Документы качества.json'
        stamp=file.stat().st_mtime_ns if file.exists() else None
        if getattr(self,'quality_stamp',object())!=stamp:
            self.quality_cache=json.loads(file.read_text('utf-8')) if file.exists() else []
            self.quality_stamp=stamp
        records=self.quality_cache
        return [r for r in records if Path(r['file']).is_file()]
    def quality_choices(self,key):
        records=self.quality_records()
        if key in ('materials','attachments'):return list(dict.fromkeys(record_text(r) for r in records))
        if key.startswith('row') and self.current:
            label=getattr(self.current,'labels',{}).get(key)
            prop={'Материал':'material','Вид документа':'type','Наименование документа':'type','Номер документа':'number','Номер':'number','Дата':'date'}.get(label)
            if prop:return list(dict.fromkeys(str(r.get(prop,'')) for r in records if r.get(prop)))
        return []
    def cancel_scan(self):
        win=getattr(self,'active_scan',None)
        if win and win.winfo_exists():win.tk.eval(win.protocol('WM_DELETE_WINDOW'))
    def refresh_quality_choices(self):
        for key,var in getattr(self,'views',{}).items():
            def find(w):
                if isinstance(w,ttk.Combobox) and str(w.cget('textvariable'))==str(var):return w
                for child in w.winfo_children():
                    result=find(child)
                    if result:return result
            widget=find(self.body[1])
            if widget:
                items=list(dict.fromkeys([*self.variants.get(key,[]),*self.quality_choices(key)]))
                widget.configure(values=items)
    def project_quality_sources(self,project):
        base=project/'Документы';found=[]
        for file in base.rglob('*'):
            if not file.is_file() or file.suffix.lower() not in ('.pdf','.jpg','.jpeg','.zip'):continue
            relative=file.relative_to(base)
            if any((parent/'Каталог.json').is_file() for parent in file.parents if parent.is_relative_to(base)):continue
            name=file.stem.casefold()
            if name.startswith(('ис-','ис ','ис_','исполнительн')):continue
            if re.match(r'^(?:(?:\d+[-_ ]+)+)?(?:кж|км|ар|ас|ов|вк|эом)(?:\W|$)',name):continue
            in_folder=any('паспорт' in part.casefold() for part in relative.parts[:-1])
            named=any(word in name for word in ('сертифик','паспорт','декларац','отказн','протокол','письмо'))
            colocated=any(p.stem.casefold().startswith(('аоср','аоок')) for p in file.parent.glob('*.xlsx'))
            if in_folder or named or colocated:found.append(file)
        return sorted(found)
    def ensure_project_passports(self,project,force=False):
        if self.project!=project or not self.root.winfo_exists():return
        if getattr(self,'active_scan',None) and self.active_scan.winfo_exists():return
        imported=[]
        base=project/'Документы'
        # A separately supplied sorted folder can be used without OCR.
        for index in base.rglob('Каталог.json'):
            try:
                data=json.loads(index.read_text('utf-8'))
                for record in data:
                    path=index.parent/record['file']
                    if path.is_file():imported.append({**record,'file':str(path)})
            except (OSError,ValueError,KeyError,TypeError):continue
        if imported:self.merge_quality_records(imported)
        known={r.get('source_hash') for r in self.quality_records()}|{sha(Path(r['file'])) for r in self.quality_records()}
        candidates=[p for p in self.project_quality_sources(project) if force or sha(p) not in known]
        if not candidates:
            self.refresh_quality_choices();return
        from scanner_ui import scanner
        scanner(self,files=candidates,destination=base)
    def merge_quality_records(self,records):
        existing=self.quality_records();keys={str(Path(r['file']).resolve()) for r in existing}
        for r in records:
            if str(Path(r['file']).resolve()) not in keys:
                existing.append(r);keys.add(str(Path(r['file']).resolve()))
        file=self.catalog_dir/'Документы качества.json';temp=file.with_suffix('.tmp')
        temp.write_text(json.dumps(existing,ensure_ascii=False,indent=2),'utf-8');temp.replace(file)
        if hasattr(self,'body') and 1 in self.body:self.refresh_quality_choices()
