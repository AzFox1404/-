"""Screen-only continuous rulers aligned to the PDF viewport."""
from tkinter import font
import re

class Guides:
    def __init__(self,view,top,left):
        self.v=view;self.top=top;self.left=left;self.hits=[];self.shown=None
        self.font=font.Font(root=left,family='Segoe UI',size=8)
        left.bind('<Button-1>',self.choose)
    def choose(self,event):
        row=next((r for a,b,r in self.hits if a<=event.y<=b),None)
        app=self.v.app;s=getattr(app,'current',None)
        if row and any(k.startswith(f'row{row}_') for k in getattr(app,'models',{}).get(s,{})):
            app.row_choice[s]=row;app.build(1);app.request_review(s,row=row);self.draw()
    def draw(self):
        v=self.v;t=self.top;l=self.left;g=getattr(v,'guides',{})
        enabled=getattr(v,'guides_enabled',g.get('kind')=='excel')
        widgets=(v.ruler_corner,t,l)
        if self.shown!=enabled:
            for widget in widgets:
                if enabled:widget.grid()
                else:widget.grid_remove()
            self.shown=enabled
        self.hits=[]
        if not enabled:return
        for c in widgets:
            c.delete('all');c.create_rectangle(0,0,max(1,c.winfo_width()),max(1,c.winfo_height()),fill='#eee7df',outline='')
        if not v.pages or v._sizes is None:return
        numbers=[r['name'] for r in g.get('rows',[])];width=max(18,max((self.font.measure(number) for number in numbers),default=self.font.measure('99'))+8)
        if int(l.cget('width'))!=width:l.configure(width=width);v.ruler_corner.configure(width=width)
        v.ruler_corner.create_line(0,19,width,19,fill='#b6ada5');v.ruler_corner.create_line(width-1,0,width-1,20,fill='#b6ada5')
        scale=v.zoom/75;viewport=v.canvas.canvasy(0);bottom=viewport+v.canvas.winfo_height()
        n=v.page_at(viewport+1);xoff=8-v.canvas.canvasx(0)
        session=getattr(v.app,'current',None);active=getattr(v.app,'row_choice',{}).get(session);column=''
        key=getattr(session,'preview_context',{}).get('activeKey','');dest=getattr(session,'spec',{}).get(key,{}).get('dest','')
        cell=re.fullmatch(r'\$?([A-Z]+)\$?(\d+)',dest) if isinstance(dest,str) else None
        if cell:column=cell[1];active=int(cell[2])
        excel=g.get('kind')=='excel' and not g.get('unsupported') and bool(g.get('rows'))
        if excel:
            rows=g['rows'];starts=sorted({int(rows[0]['name']),*(int(b) for b in g.get('breaks',[]) if int(b)>int(rows[0]['name']))})
            for page,(y,w,h,_) in enumerate(v.pages):
                if y+h<viewport or y>bottom or v.rotations.get(str(page),0):continue
                pw=v._sizes[page][0];z=g.get('zoom')
                factor=float(z)/100 if isinstance(z,(int,float)) and not isinstance(z,bool) else min(1,(pw-g['left']-g['right'])/max(1,g['width']))
                if page==n:
                    x=g['left']+((pw-g['left']-g['right']-g['width']*factor)/2 if g.get('center') else 0)
                    for c in g['cols']:
                        a=xoff+(x+c['start']*factor)*scale;b=a+c['size']*factor*scale
                        if b<0 or a>t.winfo_width():continue
                        t.create_rectangle(a,0,b,19,fill='#edcbb2' if c['name']==column else '#eee7df',outline='#b6ada5');t.create_text((a+b)/2,10,text=c['name'],font=self.font)
                first=starts[min(page,len(starts)-1)];end=starts[page+1] if page+1<len(starts) else 10**9
                origin=next((r['start'] for r in rows if int(r['name'])==first),0)
                titles=[r for r in rows if int(r['name']) in g.get('titles',[])] if page else []
                title_height=sum(r['size'] for r in titles);positions=[];offset=0
                for r in titles:positions.append((r,offset));offset+=r['size']
                positions.extend((r,title_height+r['start']-origin) for r in rows if first<=int(r['name'])<end)
                for r,offset in positions:
                    number=int(r['name']);a=y-viewport+(g['top']+offset*factor)*scale;b=a+r['size']*factor*scale
                    if b<0 or a>l.winfo_height() or b-a<2:continue
                    l.create_rectangle(0,a,width-1,b,fill='#edcbb2' if number==active else '#eee7df',outline='#b6ada5')
                    if b-a>=10:l.create_text(width/2,(a+b)/2,text=r['name'],font=self.font)
                    self.hits.append((a,b,number))
        else:
            y,w,h,_=v.pages[n];step=72/2.54*scale
            for axis,c,offset,limit in [('x',t,xoff,w),('y',l,y-viewport,h)]:
                for half in range(int(limit/step*2)+1):
                    pos=offset+half*step/2
                    if axis=='x':
                        c.create_line(pos,20,pos,12 if half%2 else 6)
                        if not half%2:c.create_text(pos,5,text=str(half//2),font=self.font)
                    else:
                        c.create_line(width,pos,width-5,pos)
                        if not half%2:c.create_text(width/2-2,pos,text=str(half//2),font=self.font)
