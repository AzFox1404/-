"""Measure actual Office export scale from matching font sizes, off the UI thread."""
from statistics import median
from collections import Counter

def calibrate(guides,pdf):
    if guides.get('kind')!='excel' or guides.get('unsupported'):return guides
    import pymupdf as fitz
    anchors={}
    for a in guides.get('anchors',[]):
        if a['text'] not in anchors:anchors[a['text']]=a['size']
        elif anchors[a['text']]!=a['size']:anchors[a['text']]=None
    unique={}
    for a in guides.get('anchors',[]):
        if a['text'] not in unique:unique[a['text']]=a
        elif unique[a['text']] and unique[a['text']].get('bottom')!=a.get('bottom'):unique[a['text']]=None
    alignments=Counter(a.get('align') for a in unique.values() if a and a.get('align') in (-4107,-4108,-4160))
    alignment=alignments.most_common(1)[0][0] if alignments else -4107
    samples=[];positions={}
    with fitz.open(stream=pdf,filetype='pdf') as doc:
        for number,page in enumerate(doc):
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines',[]):
                    for span in line['spans']:
                        size=anchors.get(span['text'].strip())
                        if size and .1<span['size']/size<4:samples.append(span['size']/size)
                        a=unique.get(span['text'].strip())
                        if a and a.get('align')==alignment:
                            point=a['bottom']-a.get('height',0)*({-4107:0,-4108:.5,-4160:1}[alignment])
                            positions.setdefault(number,[]).append(((span['bbox'][1]+span['bbox'][3])/2,point))
    if len(samples)>=3:
        scale=median(samples);agree=[s for s in samples if abs(s-scale)<.003]
        if len(agree)>=3 and len(agree)>=len(samples)*.75:
            scale=median(agree)
            # Excel rounds printed font sizes independently of grid dimensions.
            # Distant row anchors measure the grid scale without cumulative drift.
            slopes=[]
            for points in positions.values():
                for i,(y1,b1) in enumerate(points):
                    for y2,b2 in points[i+1:]:
                        if abs(b2-b1)>100:
                            slope=(y2-y1)/(b2-b1)
                            if abs(slope-scale)<.05:slopes.append(slope)
            if len(slopes)>=3:scale=median(slopes)
            offsets={n:median(y-bottom*scale for y,bottom in points) for n,points in positions.items() if len(points)>=3}
            if 0 in offsets:
                padding=offsets[0]-guides['top']
                offsets={str(n):offset-padding for n,offset in offsets.items()}
            else:offsets={}
            return dict(guides,print_scale=scale,page_offsets=offsets)
    return guides
