"""Screen-only rulers using Office print geometry; never alter the PDF."""
class Guides:
    def __init__(self,view,top,left):
        self.v=view;self.top=top;self.left=left;self.hits=[]
        left.bind('<Button-1>',self.choose)
    def choose(self,event):
        row=next((r for a,b,r in self.hits if a<=event.y<=b),None)
        app=self.v.app;s=getattr(app,'current',None)
        if row and any(k.startswith(f'row{row}_') for k in getattr(app,'models',{}).get(s,{})):
            app.row_choice[s]=row;app.build(1);app.request_review(s,row=row)
    def draw(self):
        v=self.v;t=self.top;l=self.left;t.delete('all');l.delete('all');self.hits=[]
        if not v.pages or v._sizes is None:return
        n=min(v.number,len(v.pages)-1);y,w,h,_=v.pages[n];scale=v.zoom/75
        xoff=8-v.canvas.canvasx(0);yoff=y-v.canvas.canvasy(0)
        g=getattr(v,'guides',{});session=getattr(v.app,'current',None);active=getattr(v.app,'row_choice',{}).get(session);column=''
        key=getattr(session,'preview_context',{}).get('activeKey','')
        dest=getattr(session,'spec',{}).get(key,{}).get('dest','')
        if isinstance(dest,str):
            import re
            cell=re.fullmatch(r'\$?([A-Z]+)\$?(\d+)',dest)
            if cell:column=cell[1];active=int(cell[2])
        if g.get('kind')=='excel' and not g.get('unsupported') and g.get('rows') and not v.rotations.get(str(n),0):
            pw=v._sizes[n][0];z=g.get('zoom')
            factor=float(z)/100 if isinstance(z,(int,float)) and not isinstance(z,bool) else min(1,(pw-g['left']-g['right'])/max(1,g['width']))
            x=g['left']+((pw-g['left']-g['right']-g['width']*factor)/2 if g.get('center') else 0)
            for c in g['cols']:
                a=xoff+(x+c['start']*factor)*scale;b=a+c['size']*factor*scale
                if b<0 or a>t.winfo_width():continue
                t.create_rectangle(a+34,0,b+34,22,fill='#edcbb2' if c['name']==column else '#eee7df',outline='#b6ada5');t.create_text((a+b)/2+34,11,text=c['name'])
            rows=g['rows'];starts=[int(rows[0]['name'])]+list(g.get('breaks',[]));first=starts[min(n,len(starts)-1)]
            origin=next((r['start'] for r in rows if int(r['name'])==first),0);end=starts[n+1] if n+1<len(starts) else 10**9
            for r in rows:
                number=int(r['name'])
                if not first<=number<end:continue
                a=yoff+(g['top']+(r['start']-origin)*factor)*scale;b=a+r['size']*factor*scale
                if b<0 or a>l.winfo_height() or b-a<2:continue
                l.create_rectangle(0,a,33,b,fill='#edcbb2' if number==active else '#eee7df',outline='#b6ada5')
                if b-a>=10:l.create_text(17,(a+b)/2,text=r['name'],font=('Segoe UI',8))
                self.hits.append((a,b,number))
        else:
            t.create_text(16,11,text='см',font=('Segoe UI',8))
            for axis,canvas,offset,limit in [('x',t,xoff+34,w),('y',l,yoff,h)]:
                step=72/2.54*scale
                for half in range(int(limit/step*2)+1):
                    pos=offset+half*step/2
                    if axis=='x':
                        canvas.create_line(pos,22,pos,14 if half%2 else 8)
                        if not half%2:canvas.create_text(pos,5,text=str(half//2),font=('Segoe UI',7))
                    else:
                        canvas.create_line(33,pos,25 if half%2 else 20,pos)
                        if not half%2:canvas.create_text(10,pos,text=str(half//2),font=('Segoe UI',7))
