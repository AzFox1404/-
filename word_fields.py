"""Structure-driven Word fields. Bookmarks preserve source paragraphs and tables."""
from pathlib import Path
from copy import deepcopy
import re,hashlib,json,subprocess
from datetime import datetime
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

VERSION=3
MONTHS='января февраля марта апреля мая июня июля августа сентября октября ноября декабря'.split()
DATE=re.compile(r'[«"“]?\s*\d{1,2}\s*[»"”]?\s*(?:[.\-/]\s*\d{1,2}\s*[.\-/]|(?:'+'|'.join(MONTHS)+r')\s*)\s*\d{4}\s*г?\.?',re.I)

def text(p):
    # Paragraph tab-stop settings are not text. Count only actual text runs,
    # excluding paragraphs nested in text boxes inside the current paragraph.
    result=[]
    for run in p.xpath('.//w:r'):
        parent=run.getparent()
        while parent is not None and parent.tag!=qn('w:p'):parent=parent.getparent()
        if parent is p:result.append(text_run(run))
    return ''.join(result)

def calculated(p):
    codes=p.xpath('.//w:instrText/text() | .//w:fldSimple/@w:instr')
    return any(code.lstrip().startswith('=') for code in codes)

def norm(v):return ' '.join(v.lower().split())
def caption(v):
    s=norm(v)
    return s.startswith(('(','полное и (или)','наименование строительных материалов','наименование материалов (изделий)','или строительный адрес','место проживания,','в области строительства (за исключением','номер, другие реквизиты'))

def date_value(sample):
    s=re.sub(r'[«»"“”.]',' ',sample.lower()).strip()
    digits=re.findall(r'\d+',sample)
    if len(digits)<2:return sample
    try:
        month=next((i+1 for i,m in enumerate(MONTHS) if m in s),None)
        d,m,y=(int(digits[0]),month,int(digits[-1])) if month else map(int,digits[:3])
        return datetime(y,m,d).strftime('%d.%m.%Y')
    except (ValueError,TypeError):return sample

def _run(p,value):
    r=OxmlElement('w:r');pr=p.find(qn('w:rPr'))
    if pr is not None:r.append(deepcopy(pr))
    for i,part in enumerate(re.split(r'(\t|\n)',value)):
        if not part:continue
        node=OxmlElement('w:tab' if part=='\t' else 'w:br' if part=='\n' else 'w:t')
        if part not in ('\t','\n'):node.text=part;node.set(qn('xml:space'),'preserve')
        r.append(node)
    return r

def boundary(p,offset):
    pos=0
    for r in list(p.xpath('.//w:r')):
        value=text_run(r)
        if pos<=offset<=pos+len(value) and value:
            parent=r.getparent();index=parent.index(r);cut=offset-pos
            if cut==0:return parent,index
            if cut==len(value):return parent,index+1
            left,right=_run(r,value[:cut]),_run(r,value[cut:]);parent.remove(r);parent.insert(index,left);parent.insert(index+1,right)
            return parent,index+1
        pos+=len(value)
    return p,len(p)

def text_run(r):
    return ''.join((x.text or '') if x.tag==qn('w:t') else '\t' if x.tag==qn('w:tab') else '\n' if x.tag in (qn('w:br'),qn('w:cr')) else '' for x in r.iter())

def bookmark(p,start,end,name,identifier):
    if start==end:
        parent,index=boundary(p,start)
        first=OxmlElement('w:bookmarkStart');first.set(qn('w:id'),str(identifier));first.set(qn('w:name'),name)
        last=OxmlElement('w:bookmarkEnd');last.set(qn('w:id'),str(identifier))
        parent.insert(index,first);parent.insert(index+1,last);return
    parent,index=boundary(p,end);node=OxmlElement('w:bookmarkEnd');node.set(qn('w:id'),str(identifier));parent.insert(index,node)
    parent,index=boundary(p,start);node=OxmlElement('w:bookmarkStart');node.set(qn('w:id'),str(identifier));node.set(qn('w:name'),name);parent.insert(index,node)


def analyze_word(path,prepared=None):
    d=Document(path);paras=d._element.body.xpath('.//w:p');texts=[text(p) for p in paras]
    alltext='\n'.join(texts);low=norm(alltext)
    kind='quality' if 'реестр документов качества' in low else 'act' if re.search(r'освидетельствования\s+(скрытых работ|строительных конструкций|ответственных конструкций)',low) else 'registry' if 'реестр исполнительной' in low else 'title' if 'исполнительная документация' in low else 'unknown'
    fields={};claimed=set();targets={};warnings=[];counter=0
    def add(key,label,parts,typ='text'):
        nonlocal counter
        parts=[(i,a,b) for i,a,b in parts if (i,a,b) not in claimed and not calculated(paras[i])]
        if any(texts[i][a:b].strip() for i,a,b in parts):parts=[(i,a,b) for i,a,b in parts if texts[i][a:b].strip()]
        elif len(parts)>1:parts=parts[:1]
        if not parts:return
        if key in fields:key=key+'_'+str(len(fields))
        samples=[texts[i][a:b] for i,a,b in parts];sample=' '.join(v.strip() for v in samples).strip()
        if caption(sample):return
        entries=[]
        for i,a,b in parts:
            claimed.add((i,a,b));counter+=1;name='BID_auto_'+str(counter)
            entries.append(dict(bookmark=name,sample=texts[i][a:b],capacity=max(1,b-a)))
            targets[name]=(paras[i],a,b,counter)
        fields[key]=dict(dest=entries[0]['bookmark'],segments=entries,value=date_value(sample) if typ=='worddate' else sample,label=label,kind='datecell' if typ=='worddate' else 'text',word=True,worddate=typ=='worddate',sample=sample)
    def whole(i):
        s=texts[i];a=len(s)-len(s.lstrip());b=len(s.rstrip());return (i,a,max(a,b))
    # Table headers determine editable columns; preserve the original column set.
    registry_ps=set()
    if kind in ('quality','registry'):
        for table_index,table in enumerate(d.tables,1):
            if not table.rows:continue
            headers=[norm(c.text) for c in table.rows[0].cells]
            if not any('номер' in h for h in headers):continue
            labels=[]
            for h in headers:
                labels.append('Материал' if 'материал' in h else 'Вид документа' if 'подтвержда' in h else 'Номер документа' if 'номер' in h and 'п/п' not in h else 'Дата' if 'дата' in h else 'Количество листов' if 'лист' in h else 'Наименование документа' if 'наименование' in h else None)
            for rn,row in enumerate(table.rows[1:],2):
                if any(re.search(r'всего|итого',c.text,re.I) for c in row.cells):continue
                first=row.cells[0].text.strip()
                if not first.isdigit() and first:continue
                for col,(cell,label) in enumerate(zip(row.cells,labels),1):
                    if col==1 or not label:continue
                    parts=[]
                    for p in cell._tc.xpath('.//w:p'):
                        i=next((i for i,node in enumerate(paras) if node is p),None)
                        if i is not None:parts.append(whole(i));registry_ps.add(i)
                    key=f'row{rn}_{col}'
                    add(key,label,parts,'worddate' if label=='Дата' else 'text')
                    if key in fields:fields[key].update(wordTable=table_index,wordColumn=col)
    def heading(v):
        s=norm(v)
        if s.startswith('объект капитального строительства'):return 'address','Объект и адрес'
        if s.startswith('застройщик,'):return 'client','Застройщик · реквизиты'
        if s.startswith('лицо, осуществляющее строительство'):return 'builder','Подрядчик · реквизиты'
        if s.startswith('лицо, осуществляющее подготовку проектной'):return 'designer','Проектировщик · реквизиты'
        if s.startswith('представител'):
            role='developer' if 'застройщика' in s else 'designerRep' if 'подготовку проектной' in s else 'executorRep' if 'выполнившего работы' in s else 'controlRep' if 'строительного контроля' in s else 'builderRep'
            labels={'developer':'Представитель застройщика','designerRep':'Представитель проектировщика','executorRep':'Представитель исполнителя','controlRep':'Строительный контроль подрядчика','builderRep':'Представитель подрядчика'}
            return role,labels[role]
        rules=[(r'^1\.\s*к освидетельствованию','work','Освидетельствованные работы / конструкции'),(r'^2\.','project','Рабочая и проектная документация'),(r'^3\.\s*при выполнении','materials','Материалы и документы качества'),(r'^3\.\s*освидетельствованы','hiddenWorks','Освидетельствованные скрытые работы'),(r'^4\.\s*при выполнении','materials','Материалы и документы качества'),(r'^4\.\s*предъявлены','schemes','Исполнительные схемы и подтверждающие документы'),(r'^а\)\s*исполнительные','schemes','Исполнительные схемы'),(r'^б\)\s*результаты','reports','Результаты экспертиз и обследований'),(r'^6\.\s*проведены','tests','Испытания'),(r'^(?:6\.\s*работы выполнены|8\.\s*предъявленные)','standards','Нормативные документы'),(r'^(?:7\.\s*разрешается|б\)\s*разрешается)','nextWork','Последующие работы'),(r'^дополнительные сведения','notes','Дополнительные сведения'),(r'^приложения\s*:?$','attachments','Приложения')]
        for pat,k,l in rules:
            if re.search(pat,s):return k,l
    # Values follow a semantic heading and stop before its small-print explanation.
    seen_roles=set()
    for i,value in enumerate(texts):
        if i in registry_ps:continue
        h=heading(value)
        if not h:continue
        key,label=h
        if key.endswith('Rep') or key=='developer':
            if key in seen_roles:key=key+'Sign';label+=' · подпись / ФИО'
            else:seen_roles.add(key)
        inline=value.find('\n')
        parts=[]
        note=re.match(r'^\s*Дополнительные сведения\s*:?\s*(.+)$',value,re.I) if key=='notes' else None
        if note:parts=[(i,note.start(1),note.end(1))]
        elif inline>=0 and value[:inline].strip() and value[inline+1:].strip() and not caption(value[inline+1:]) and not heading(value[inline+1:]):parts=[(i,inline+1,len(value.rstrip()))]
        else:
            for j in range(i+1,min(i+8,len(texts))):
                s=texts[j].strip()
                if caption(s) or heading(s) or re.match(r'^\d+\.',s) or s.startswith(('АКТ','и составили','Акт составлен','5. Даты')):break
                if not s:
                    if not parts:parts.append(whole(j))
                    continue
                if s in ('№','"','«','»'):break
                parts.append(whole(j))
        if not parts and key in ('notes','attachments'):parts=[(i,len(value),len(value))]
        if parts:add(key,label,parts)
    # Inline entries retain their label and surrounding punctuation.
    for i,value in enumerate(texts):
        if i in registry_ps or caption(value):continue
        for pattern,key,label in [(r'начала работ\s*','workStart','Начало работ'),(r'окончания работ\s*','workEnd','Окончание работ')]:
            m=re.search(pattern,value,re.I)
            if m:
                date=DATE.search(value,m.end())
                if date:add(key,label,[(i,date.start(),date.end())],'worddate')
        m=re.search(r'произвели осмотр работ, выполненных\s*:?\s*([^:\s].*)',value,re.I)
        if m:add('executor','Исполнитель работ',[(i,m.start(1),len(value.rstrip()))])
        elif re.search(r'произвели осмотр работ, выполненных',value,re.I) and i+1<len(texts):
            j=next((j for j in range(i+1,min(i+5,len(texts))) if texts[j].strip()),None)
            if j is not None and not caption(texts[j]):add('executor','Исполнитель работ',[whole(j)])
        m=re.search(r'Акт составлен в\s*(\d+)',value,re.I)
        if m:add('copies','Количество экземпляров',[(i,m.start(1),m.end(1))])
        m=re.search(r'нагружением в размере\s*(\d+\s*%)',value,re.I)
        if m:add('loadPercent','Допустимая нагрузка',[(i,m.start(1),m.end(1))])
    def date_parts(i):
        chunk=list(range(i,min(i+14,len(texts))))
        day=next((j for j in chunk if re.fullmatch(r'\s*\d{1,2}\s*',texts[j])),None)
        month=next((j for j in chunk if any(m in texts[j].lower() for m in MONTHS)),None)
        if day is None or month is None:return []
        year=next((j for j in chunk if re.search(r'\d{4}',texts[j])),None)
        if year is None:return []
        return [whole(j) for j in dict.fromkeys((day,month,year))]
    for i,v in enumerate(texts):
        for marker,key,label in [('начала работ','workStart','Начало работ'),('окончания работ','workEnd','Окончание работ')]:
            if marker in v and key not in fields:
                parts=date_parts(i+1)
                if parts:add(key,label,parts,'worddate')
        if re.search(r'Акт составлен в\s*$',v,re.I) and i+1<len(texts) and texts[i+1].strip().isdigit():add('copies','Количество экземпляров',[whole(i+1)])
        if norm(v).startswith(('ассоциация','сро ')) and not any((i,a,b) in claimed for _,a,b in [whole(i)]):
            add('sro'+str(i),'СРО · реквизиты',[whole(i)])
    if kind=='act':
        # Number and date are usually in a compact table directly under the title.
        for i,v in enumerate(texts):
            if re.fullmatch(r'\s*№?\s*(?:АООК-)?[А-ЯA-Z]{1,8}[-–]\d+\s*',v):
                m=re.search(r'(?:АООК-)?[А-ЯA-Z]{1,8}[-–]\d+',v);add('number','Номер акта',[(i,m.start(),m.end())]);break
        for i,v in enumerate(texts):
            if caption(v):continue
            hit=DATE.search(v)
            if hit and i<next((n for n,s in enumerate(texts) if 'Представитель' in s),len(texts)):
                add('actDate','Дата акта',[(i,hit.start(),hit.end())],'worddate');break
            if re.fullmatch(r'\s*\d{1,2}\s*',v) and i+2<len(texts):
                for j in range(i+1,min(i+4,len(texts))):
                    if any(m in texts[j].lower() for m in MONTHS) and re.search(r'\d{4}',texts[j]):
                        parts=date_parts(i)
                        if parts:add('actDate','Дата акта',parts,'worddate')
                        break
                if 'actDate' in fields:break
        if 'actDate' not in fields:
            limit=next((n for n,v in enumerate(texts) if norm(v).startswith('представитель')),len(texts))
            for i in range(limit):
                if not re.fullmatch(r'\s*\d{1,2}\s*',texts[i]):continue
                parts=date_parts(i)
                if parts and all(n<limit for n,a,b in parts):add('actDate','Дата акта',parts,'worddate');break
    if kind in ('quality','registry','title'):
        for i,v in enumerate(texts):
            if i in registry_ps or caption(v) or not v.strip():continue
            if re.match(r'^\s*(приложение\s*№|реестр документов качества)',v,re.I):
                m=re.search(r'№\s*(\d+)',v)
                if m:add('appendixNumber' if 'приложение' in v.lower() else 'qualityNumber','Номер приложения' if 'приложение' in v.lower() else 'Номер реестра качества',[(i,m.start(1),m.end(1))])
            elif re.match(r'^к акту',v,re.I):
                match=re.search(r'№\s*(.+?)\s+от\s+',v,re.I)
                if match:add('actRef','Номер связанного акта',[(i,match.start(1),match.end(1))])
                date=DATE.search(v)
                if date:add('refDate','Дата связанного акта',[(i,date.start(),date.end())],'worddate')
                obj=re.search(r'на объекте\s+(.+)$',v,re.I)
                if obj:add('regAddress','Объект и адрес',[(i,obj.start(1),obj.end(1))])
                work=re.search(r'освидетельствования (?:скрытых работ|строительных конструкций)\s+[«\"](.+?)[»\"]\s+на объекте',v,re.I)
                if work:add('refWork','Работы / конструкции связанного акта',[(i,work.start(1),work.end(1))])
            elif re.match(r'^\s*составил',v,re.I):
                m=re.match(r'^\s*Составил\s*:\s*',v,re.I);add('compilerRole','Составил · должность',[(i,m.end(),len(v))])
                if i+1<len(texts):add('compiler','Составил · организация и ФИО',[whole(i+1)])
            elif kind=='title':
                m=re.match(r'^(\s*(?:ЗАКАЗЧИК:|Объект:|шифр проекта)\s*)(.*)$',v,re.I)
                if m:
                    key='titleClient' if m[1].strip().lower().startswith('заказчик') else 'titleAddress' if m[1].strip().lower().startswith('объект') else 'code'+str(1+sum(k.startswith('code') for k in fields))
                    add(key,m[1].rstrip(':'),[(i,m.start(2),len(v))])
                elif re.match(r'^г\.\s',v):add('cityYear','Город и год',[whole(i)])
                elif v.strip()=='Раздел' and i+1<len(texts):add('section'+str(1+sum(k.startswith('section') for k in fields)),'Раздел',[whole(i+1)])
    from manual_fields import apply as apply_manual,revision as manual_revision
    added_manual=apply_manual(d,add,claimed)
    if kind=='unknown' and added_manual:kind='custom'
    if kind=='unknown':
        fields={};targets={}
        warnings.append('Тип формы не распознан. Поля не назначены автоматически, чтобы не изменить постоянный текст.')
    if kind=='act' and 'скрытых работ' in low and re.search(r'к АООК\b',alltext):warnings.append('В АОСР найдена ссылка на приложение к АООК. Проверьте вид связанного акта перед исправлением поля «Приложения».')
    if 'АОСК' in Path(path).name.upper() and 'АООК' in alltext:warnings.append('В названии файла указано АОСК, в содержимом — АООК. Исходные обозначения сохранены; уточните вид документа.')
    if kind=='act':
        order=['address','client','builder','designer']+[k for k in fields if k.startswith('sro')]+['number','actDate','developer','builderRep','controlRep','designerRep','executorRep','otherRep','executor','work','project','hiddenWorks','materials','schemes','reports','tests','workStart','workEnd','standards','loadPercent','nextWork','notes','copies','attachments','developerSign','builderRepSign','controlRepSign','designerRepSign','executorRepSign']
        for key,label in [('actDate','Дата акта'),('workStart','Начало работ'),('workEnd','Окончание работ')]:
            if key not in fields:warnings.append(label+': не удалось уверенно определить место заполнения. Проверьте форму перед использованием.')
    elif kind in ('quality','registry'):
        order=['appendixNumber','actRef','refDate','refWork','regAddress','qualityNumber']+[k for k in fields if k.startswith('row')]+['compilerRole','compiler']
    else:order=[]
    fields={key:fields[key] for key in dict.fromkeys(order+list(fields)) if key in fields}
    # Unsupported values are not made editable merely because they contain text.
    if prepared:
        ids={node.get(qn('w:id')) for node in d._element.xpath('.//w:bookmarkStart') if node.get(qn('w:name'),'').startswith('BID_auto_')}
        for node in list(d._element.xpath('.//w:bookmarkStart | .//w:bookmarkEnd')):
            if node.get(qn('w:id')) in ids:node.getparent().remove(node)
        existing=[int(node.get(qn('w:id'),'0')) for node in d._element.xpath('.//w:bookmarkStart') if node.get(qn('w:id'),'').isdigit()]
        base=max([10000]+existing)+1
        for name,(p,a,b,ident) in targets.items():bookmark(p,a,b,name,base+ident)
        d.save(prepared)
    return dict(kind=kind,fields=fields,warnings=warnings,version=VERSION,manualRevision=manual_revision())


def prepare_word(source,directory):
    source=Path(source).resolve();directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True)
    docx=source
    if source.suffix.lower()=='.doc':
        docx=directory/'converted.docx'
        r=subprocess.run(['powershell.exe','-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',str(Path(__file__).with_name('ConvertWord.ps1')),'-Source',str(source),'-Target',str(docx)],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=90)
        if r.returncode:raise RuntimeError('Не удалось прочитать DOC через Microsoft Word: '+r.stderr.decode('utf-8',errors='replace')[:300])
    prepared=directory/'prepared.docx';plan=analyze_word(docx,prepared);plan['prepared']=str(prepared)
    if 'АОСК' in source.name.upper() and 'АООК' in ' '.join(v['value'] for v in plan['fields'].values()):plan['warnings'].append('В названии файла указано АОСК, в содержимом — АООК. Обозначения сохранены до подтверждения исправления.')
    return plan
