import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile
from pypdf import PdfReader, PdfWriter
import pypdfium2 as pdfium
from PIL import Image, ImageOps, ImageFilter

TYPES=['Паспорт качества','Сертификат качества','Сертификат соответствия','Декларация о соответствии','Протокол испытаний','Отказное письмо','Информационное письмо','Свидетельство','Документ']
HEADER=re.compile(r'(паспорт(?:\s+качества)?|сертификат\s+(?:качества|соответствия)|декларация(?:\s+о\s+соответствии)?|протокол\s+испытаний|отказное\s+письмо|информационное\s+письмо|свидетельство)',re.I)
DATE=r'(\d{1,2})\s*[.\-/]\s*(\d{1,2})\s*[.\-/]\s*(\d{4})(?!\d)'
MONTHS='января февраля марта апреля мая июня июля августа сентября октября ноября декабря'.split()

def propose(text):
    text=re.sub(r'(?m)^\s*\d{1,2}\.\d{1,2}\.\d{4}\s*,[^\n]*','',text)
    m=HEADER.search(text)
    if not m:return None
    title=m[0].lower()
    typ=next((t for t in TYPES if t.lower()==title),m[0].strip().capitalize())
    number=''
    for header in HEADER.finditer(text):
        if header[0].lower()!=title:continue
        tail=text[header.end():header.end()+110]
        mark=re.match(r'\s*(?:№|N[o°]?|#)\s*([\w./-]+)',tail,re.I)
        bare=re.match(r'\s*(?:[НШ][!]?\s*)?(\d{2,}[\w/-]*)(?![.\d])',tail)
        if mark or bare:
            number=(mark or bare)[1].rstrip('.');break
    issued=re.search(r'(?:дата\s+(?:выписки|выдачи|составления)[^\n]{0,30}?|\bот\s+)'+DATE,text,re.I)
    if not issued:
        dates=list(re.finditer(DATE,text[m.end():]))
        issued=dates[0] if len(set(x[0] for x in dates))==1 and not re.search(r'печати[^\n]*'+DATE,text,re.I) else None
    date=''
    if issued:
        try:date=dt.date(int(issued[3]),int(issued[2]),int(issued[1])).strftime('%d.%m.%Y')
        except ValueError:pass
    if not date:
        verbal=re.findall(r'[«"]?\s*(\d{1,2})\s*[»"]?\s+('+'|'.join(MONTHS)+r')\s+(\d{4})',text.lower())
        if len(verbal)==1:
            d,m,y=verbal[0];date=f'{int(d):02}.{MONTHS.index(m)+1:02}.{y}'
    return typ,number,date

def safe_name(value):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',value).strip(' .')[:155] or 'Документ'

def inputs(files,tmp):
    for path in files:
        if path.suffix.lower()=='.zip':
            with zipfile.ZipFile(path) as archive:
                for i,m in enumerate(archive.infolist()):
                    suffix=Path(m.filename).suffix.lower()
                    if m.is_dir() or suffix not in ('.pdf','.jpg','.jpeg'):continue
                    dest=tmp/f'{path.stem}_{i}{suffix}'
                    with archive.open(m) as src,dest.open('wb') as out:shutil.copyfileobj(src,out)
                    yield dest,m.filename
        else:yield path,path.name

def inspect(files,tmp,notify,cache=None):
    records=[];ocr=None
    try:
        for ix,(path,name) in enumerate(inputs(files,tmp)):
            if path.suffix.lower()!='.pdf':
                with Image.open(path) as image:image.convert('RGB').save(tmp/f'image{ix}.pdf')
                path=tmp/f'image{ix}.pdf'
            reader=PdfReader(path);pdf=pdfium.PdfDocument(path)
            pages=[]
            try:
                cached=None
                if cache:
                    cache.mkdir(parents=True,exist_ok=True)
                    with path.open('rb') as src:digest=hashlib.file_digest(src,'sha256').hexdigest()
                    cached=cache/(digest+'-v2.json')
                    if cached.exists():
                        try:pages=json.loads(cached.read_text('utf-8'))
                        except (OSError,ValueError):pages=[]
                    if not isinstance(pages,list) or len(pages)!=len(reader.pages):pages=[]
                    if pages:notify(f'{name} · результаты сохранённого распознавания')
                for n,page in enumerate(reader.pages if not pages else []):
                    notify(f'{name} · страница {n+1} из {len(reader.pages)}')
                    text=page.extract_text() or ''
                    if len(text.strip())<35:
                        if ocr is None:
                            ocr=subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(Path(__file__).with_name('PassportOCR.ps1'))],
                                stdin=subprocess.PIPE,stdout=subprocess.PIPE,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
                        raster=pdf[n];bmp=raster.render(scale=min(2.6,2400/max(raster.get_size())))
                        imgfile=tmp/f'page-{ix}-{n}.png';bmp.to_pil().convert('RGB').save(imgfile);bmp.close();raster.close()
                        ocr.stdin.write(str(imgfile.resolve())+'\n');ocr.stdin.flush()
                        result=json.loads(ocr.stdout.readline().lstrip('\ufeff'))
                        if 'error' in result:raise ValueError(result['error'])
                        text=result['text']
                        # A washed-out scan can group the number into the wrong OCR column.
                        # Read the upper part again with increased contrast before grouping pages.
                        if HEADER.search(text):
                            with Image.open(imgfile) as img:
                                region=img.crop((0,0,img.width,int(img.height*.30)))
                                region=ImageOps.autocontrast(region.convert('L')).filter(ImageFilter.SHARPEN)
                                region.thumbnail((2000,1300));focused=tmp/f'heading-{ix}-{n}.png';region.save(focused)
                            ocr.stdin.write(str(focused.resolve())+'\n');ocr.stdin.flush()
                            head=json.loads(ocr.stdout.readline().lstrip('\ufeff')).get('text','')
                            if HEADER.search(head):text=head+'\n'+text
                    pages.append(text)
                if cached and not cached.exists():
                    with tempfile.NamedTemporaryFile(dir=cached.parent,delete=False,mode='w',encoding='utf-8') as out:
                        json.dump(pages,out,ensure_ascii=False)
                    Path(out.name).replace(cached)
            finally:pdf.close()
            cuts=[]
            for n,text in enumerate(pages):
                hit=propose(text)
                if n==0 or (hit and (hit[0]!=cuts[-1][1][0] or hit[1] and hit[1]!=cuts[-1][1][1])):
                    boundary=n
                    if cuts and n>cuts[-1][0]+1 and hit and hit[1]:
                        prior=propose(pages[n-1])
                        if prior and prior[0]==hit[0] and not prior[1]:boundary=n-1
                    cuts.append((boundary,hit or ('Документ','','')))
            for j,(start,(kind,number,date)) in enumerate(cuts):
                end=cuts[j+1][0] if j+1<len(cuts) else len(pages)
                for evidence in pages[start:end]:
                    alternative=propose(evidence)
                    if alternative and alternative[0]==kind:
                        number=number or alternative[1];date=date or alternative[2]
                material=''
                evidence=' '.join(pages[start:end])
                for pattern in [r'Двутавр\s+(\d{1,3}[БКШ]\d)',r'(Грунт[- ]эмаль)',r'(Уголок)\s+(\d+[хx×]\d+[хx×]\d+)']:
                    match=re.search(pattern,evidence,re.I)
                    if match:material=match[0];break
                records.append(dict(path=str(path),source=name,start=start+1,end=end,type=kind,number=number,date=date,material=material,pages=pages))
    finally:
        if ocr:ocr.stdin.close();ocr.wait()
    if not records:raise ValueError('В источнике нет PDF или JPEG.')
    return records

def save_records(records,dest):
    dest=Path(dest);dest.mkdir(exist_ok=True,parents=True)
    used={p.name for p in dest.iterdir() if p.is_dir()}
    seq=1
    while f'{seq}. Паспорта' in used:seq+=1
    folder=dest/f'{seq}. Паспорта'
    staged=Path(tempfile.mkdtemp(dir=dest))
    metadata=[]
    try:
        for i,rec in enumerate(records,1):
            reader=PdfReader(rec['path']);w=PdfWriter()
            for n in range(rec['start']-1,rec['end']):
                page=reader.pages[n];angle=rec.get('rotations',{}).get(str(n),0)
                if angle:page.rotate(angle)
                w.add_page(page)
            kind=rec['type'];group=('Сертификаты' if 'сертификат' in kind.lower() else 'Паспорта' if 'паспорт' in kind.lower() else 'Декларации' if 'деклараци' in kind.lower() else 'Прочее')
            sub=staged/group;sub.mkdir(exist_ok=True)
            label=kind+((' №'+rec['number']) if rec['number'] else ' б/н')+((' от '+rec['date']) if rec['date'] else '')
            if not rec['number'] and not rec['date'] and rec['material']:label=rec['material']
            target=sub/f'{i}. {safe_name(label)}.pdf'
            with target.open('wb') as out:w.write(out)
            metadata.append({**{k:rec[k] for k in ('source','start','end','type','number','date','material')},'file':str(target.relative_to(staged)), 'source_hash':hashlib.sha256(Path(rec['path']).read_bytes()).hexdigest()})
        (staged/'Каталог.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),'utf-8')
        staged.rename(folder)
    except Exception:
        shutil.rmtree(staged,ignore_errors=True);raise
    return folder,metadata


