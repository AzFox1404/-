"""Conservative on-screen-only replacements. No document or PDF is modified."""
import re
from collections import Counter

def eligible(values,labels):
    result={}
    for key,value in values.items():
        value=str(value)
        label=labels.get(key,'')
        if not 3<=len(value)<=300 or '\n' in value:continue
        result[key]=value
        if len(result)>=64:break # Bound whole-PDF anchor search on large registers.
    return result

def locate(doc,values):
    """Called only inside the PDF renderer process; reject ambiguous locations."""
    import pymupdf as fitz
    duplicates=Counter(values.values());hits={k:[] for k in values}
    for n,page in enumerate(doc):
        if page.rotation:continue
        tp=page.get_textpage();spans=[];rules=[]
        for drawing in page.get_drawings():
            dr=drawing['rect']
            if dr.height<=1 and dr.width>1:rules.append((dr.x0,dr.x1,(dr.y0+dr.y1)/2))
            for item in drawing['items']:
                if item[0]=='l' and abs(item[1].y-item[2].y)<.2:rules.append((min(item[1].x,item[2].x),max(item[1].x,item[2].x),item[1].y))
        for block in page.get_text('dict',textpage=tp)['blocks']:
            for line in block.get('lines',[]):
                if tuple(line.get('dir',(1,0)))!=(1,0):continue
                spans.extend(line['spans'])
        for key,value in values.items():
            if duplicates[value]>1:continue
            rects=page.search_for(value,textpage=tp)
            for r in rects:
                def exact_part(s):
                    pos=s['text'].find(value)
                    if pos<0:return False
                    after=pos+len(value)
                    return not (value[0].isalnum() and pos and s['text'][pos-1].isalnum() or value[-1].isalnum() and after<len(s['text']) and s['text'][after].isalnum())
                span=next((s for s in spans if exact_part(s) and fitz.Rect(s['bbox']).contains(r)),None)
                if not span or r.height>span['size']*1.7:continue
                if any(x0<r.x1 and x1>r.x0 and r.y0<=y<=r.y1 for x0,x1,y in rules):continue
                hits[key].append(dict(page=n,rect=(r.x0/page.rect.width,r.y0/page.rect.height,r.x1/page.rect.width,r.y1/page.rect.height),font=span['font'],size=span['size'],flags=span['flags']))
    return {k:v[0] for k,v in hits.items() if len(v)==1}

def family(name):
    name=name.split('+')[-1].lower()
    for token,font in [('times','Times New Roman'),('arial','Arial'),('helvetica','Arial'),('calibri','Calibri'),('courier','Courier New')]:
        if token in name:return font
