"""Local structural exemplars. Exact matches supplement, never replace known fields."""
from pathlib import Path
import json,hashlib,re
from functools import lru_cache
from app_paths import DATA_DIR

FILE=DATA_DIR/'Библиотека'/'Образцы форм.json'
PERSONAL=DATA_DIR/'Библиотека'/'Личные варианты.json'

@lru_cache(maxsize=4)
def _profiles(path,stamp,size):
    return read(path).get('profiles',[])

def profiles():
    try:s=FILE.stat();return _profiles(str(FILE),s.st_mtime_ns,s.st_size)
    except OSError:return []

def read(path):
    try:return json.loads(Path(path).read_text('utf-8-sig'))
    except (OSError,ValueError):return {}

def save(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf-8');tmp.replace(path)

def word_shape(doc):
    return [len(doc._element.body.xpath('.//w:p')),[[len(r.cells) for r in t.rows] for t in doc.tables]]

def word_profile(prepared,fields):
    from docx import Document
    from word_fields import text,caption
    from docx.oxml.ns import qn
    d=Document(prepared);ps=d._element.body.xpath('.//w:p');locations={}
    for i,p in enumerate(ps):
        offset=0;starts={}
        for node in p.iter():
            if node.tag==qn('w:bookmarkStart'):starts[node.get(qn('w:id'))]=(node.get(qn('w:name')),offset)
            elif node.tag==qn('w:bookmarkEnd') and node.get(qn('w:id')) in starts:
                name,a=starts[node.get(qn('w:id'))];locations[name]=(i,a,offset)
            elif node.tag==qn('w:t'):offset+=len(node.text or '')
            elif node.tag in (qn('w:tab'),qn('w:br'),qn('w:cr')):offset+=1
    rules=[];mutable=set()
    for key,f in fields.items():
        if key.startswith('row'):continue # table rows use the existing column-aware path
        slots=[]
        for part in f.get('segments',[]):
            found=locations.get(part.get('bookmark'))
            if not found:break
            i,a,b=found;v=text(ps[i])
            if caption(v):break
            slots.append(dict(paragraph=i,prefix=v[:a],suffix=v[b:]))
        else:
            if slots:
                rules.append(dict(key=key,label=f['label'],date=f.get('worddate',False),slots=slots))
                mutable.update(s['paragraph'] for s in slots)
    guards={str(i):text(p) for i,p in enumerate(ps) if i not in mutable}
    return dict(format='word',shape=word_shape(d),guards=guards,rules=rules,provenance='existing-confirmed-bindings')

def word_matches(doc,profile,near=False,context=None):
    from word_fields import text
    shape,values=context if context is not None else (word_shape(doc),[text(p) for p in doc._element.body.xpath('.//w:p')])
    if profile.get('format')!='word' or profile['shape']!=shape:return False
    guards=profile['guards']
    hits=sum(values[int(i)]==v for i,v in guards.items())
    return bool(guards) and (hits==len(guards) if not near else hits>=max(3,len(guards)*.85))

def apply_word(doc,add,claimed,existing):
    from word_fields import text,caption
    ps=doc._element.body.xpath('.//w:p');proposals={};before=len(existing)
    context=(word_shape(doc),[text(p) for p in ps])
    for profile in profiles():
        if not word_matches(doc,profile,context=context):continue
        for rule in profile['rules']:
            key=rule['key']
            if key in existing:continue
            parts=[]
            for slot in rule['slots']:
                i=slot['paragraph'];v=text(ps[i]);prefix=slot['prefix'];suffix=slot['suffix']
                if not v.startswith(prefix) or suffix and not v.endswith(suffix) or caption(v):break
                a=len(prefix);b=len(v)-len(suffix)
                if b<a or any(j==i and (a<y and b>x or a==b==x==y) for j,x,y in claimed):break
                parts.append((i,a,b))
            else:
                candidate=(rule['label'],tuple(parts),rule['date'])
                if key in proposals and proposals[key]!=candidate:proposals[key]=None
                elif key not in proposals:proposals[key]=candidate
    for key,candidate in proposals.items():
        if candidate:
            label,parts,date=candidate;add(key,label,list(parts),'worddate' if date else 'text')
    return len(existing)>before

def excel_profile(sheet,fields):
    destinations={f['dest'] for f in fields.values() if re.fullmatch(r'[A-Z]+\d+',f.get('dest',''))}
    guards={c.coordinate:str(c.value) for row in sheet for c in row if c.value is not None and c.coordinate not in destinations}
    rules=[dict(key=k,cell=f['dest'],label=f['label'],kind=f.get('kind','text'),prefix=f.get('prefix','')) for k,f in fields.items() if f.get('dest') in destinations]
    return dict(format='excel',sheet=sheet.title,shape=[sheet.max_row,sheet.max_column,sorted(str(m) for m in sheet.merged_cells.ranges)],guards=guards,rules=rules,provenance='existing-confirmed-bindings')

def apply_excel(sheet,existing):
    from office_forms import instruction
    shape=[sheet.max_row,sheet.max_column,sorted(str(m) for m in sheet.merged_cells.ranges)]
    proposals={}
    for p in profiles():
        if p.get('format')!='excel' or p.get('sheet')!=sheet.title or p['shape']!=shape or not p['guards']:continue
        if any(str(sheet[c].value)!=v for c,v in p['guards'].items()):continue
        for rule in p['rules']:
            c=sheet[rule['cell']]
            if rule['key'] in existing or c.coordinate in {f['dest'] for f in existing.values()} or c.__class__.__name__=='MergedCell' or c.data_type=='f' or instruction(c.value):continue
            value=c.value.strftime('%d.%m.%Y') if hasattr(c.value,'strftime') else str(c.value or '')
            prefix=rule.get('prefix','')
            if prefix and value.startswith(prefix):value=value[len(prefix):]
            key=rule['key'];candidate={**rule,'dest':c.coordinate,'value':value}
            if key in proposals and proposals[key]!=candidate:proposals[key]=None
            elif key not in proposals:proposals[key]=candidate
    existing.update({k:v for k,v in proposals.items() if v})
    return existing

def personal_choices(key,label,data):
    aliases={'titleClient':'client','developerSign':'clientSign','builderRepSign':'foreman','executorRepSign':'executorSign'}
    canonical=aliases.get(key,key)
    companies=data.get('organizations',[]) if canonical in ('client','builder','designer','executor','regFirm') else []
    return list(dict.fromkeys([*data.get('keys',{}).get(canonical,[]),*data.get('labels',{}).get(label,[]),*companies]))

def revision():
    return hashlib.sha256(FILE.read_bytes() if FILE.exists() else b'').hexdigest()

def remember(profile):
    if not profile.get('rules'):return
    identity=hashlib.sha256(json.dumps(profile,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    data=read(FILE);profiles=data.setdefault('profiles',[])
    if not any(p.get('id')==identity for p in profiles):
        profiles.append(dict(profile,id=identity));data['version']=1;save(FILE,data)

def suggestions_word(doc):
    """Near matches only assist the explicit manual confirmation dialog."""
    result={}
    from word_fields import text
    context=(word_shape(doc),[text(p) for p in doc._element.body.xpath('.//w:p')])
    for profile in profiles():
        if not word_matches(doc,profile,near=True,context=context):continue
        for rule in profile['rules']:
            for slot in rule['slots']:
                i=slot['paragraph'];candidate=dict(slot,label=rule['label'])
                if i in result and result[i]!=candidate:result[i]=None
                elif i not in result:result[i]=candidate
    return {i:v for i,v in result.items() if v}

def suggestions_excel(sheet):
    shape=[sheet.max_row,sheet.max_column,sorted(str(m) for m in sheet.merged_cells.ranges)]
    result={}
    for p in profiles():
        if p.get('format')!='excel' or p.get('sheet')!=sheet.title or p['shape']!=shape:continue
        guards=p['guards'];hits=sum(str(sheet[c].value)==v for c,v in guards.items())
        if hits<max(3,len(guards)*.85):continue
        for rule in p['rules']:
            c=rule['cell'];label=rule['label']
            if c in result and result[c]!=label:result[c]=None
            elif c not in result:result[c]=label
    return {c:v for c,v in result.items() if v}
