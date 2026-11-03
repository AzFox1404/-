"""Compact rounded scrollbar with bounded hover animation and standard commands."""
import tkinter as tk
from tkinter import ttk
import time

class Scrollbar(tk.Canvas):
    def __init__(self,master,orient='vertical',command=None,**kwargs):
        self.vertical=orient not in ('horizontal',tk.HORIZONTAL);self.command=command
        super().__init__(master,highlightthickness=0,bd=0,takefocus=True,**({'width':12} if self.vertical else {'height':12}),**kwargs)
        self.first=0.;self.last=1.;self.hot=0.;self.job=None;self.drag=None
        self.bind('<Configure>',lambda e:self.redraw_theme())
        self.bind('<Enter>',lambda e:self.animate(1));self.bind('<Leave>',lambda e:self.animate(0) if self.drag is None else None)
        self.bind('<ButtonPress-1>',self.press);self.bind('<B1-Motion>',self.move);self.bind('<ButtonRelease-1>',self.release)
        self.bind('<MouseWheel>',lambda e:self.command('scroll',-3 if e.delta>0 else 3,'units') if self.command else None)
        def arrow(e,step):
            if self.command:self.command('scroll',step,'units')
            return 'break'
        for key,step in [('Up',-1),('Left',-1),('Down',1),('Right',1)]:self.bind('<'+key+'>',lambda e,s=step:arrow(e,s))
        self.bind('<Destroy>',self.dispose);self.redraw_theme()
    def set(self,first,last):self.first=float(first);self.last=float(last);self.redraw_theme()
    def get(self):return self.first,self.last
    def geometry(self):
        length=max(1,(self.winfo_height() if self.vertical else self.winfo_width())-6)
        size=min(length,max(24,length*(self.last-self.first)))
        start=3+(length-size)*self.first/max(.0001,1-(self.last-self.first))
        return start,size,max(1,length-size)
    def redraw_theme(self):
        if not self.winfo_exists():return
        bg=ttk.Style(self).lookup('TFrame','background') or '#faf5f1';self.configure(bg=bg);self.delete('all')
        if self.last-self.first>=.999:return
        start,size,_=self.geometry();wide=4+4*self.hot;middle=(self.winfo_width() if self.vertical else self.winfo_height())/2
        box=(middle-wide/2,start,middle+wide/2,start+size) if self.vertical else (start,middle-wide/2,start+size,middle+wide/2)
        a,b,c,d=box;r=wide/2;fill='#a8968a' if self.hot<.5 else '#806c5f'
        self.create_polygon(a+r,b,c-r,b,c,b,c,b+r,c,d-r,c,d,c-r,d,a+r,d,a,d,a,d-r,a,b+r,a,b,smooth=True,splinesteps=8,fill=fill,outline='')
    def animate(self,target):
        if self.job is not None:self.after_cancel(self.job)
        start=self.hot;began=time.monotonic()
        def tick():
            self.job=None;t=min(1,(time.monotonic()-began)/.12);self.hot=start+(target-start)*t;self.redraw_theme()
            if t<1:self.job=self.after(16,tick)
        tick()
    def press(self,e):
        self.focus_set();pos=e.y if self.vertical else e.x;start,size,_=self.geometry();self.animate(1)
        if start<=pos<=start+size:self.drag=(pos,self.first)
        elif self.command:self.command('scroll',-1 if pos<start else 1,'pages')
    def move(self,e):
        if self.drag and self.command:
            pos=e.y if self.vertical else e.x;_,_,travel=self.geometry();span=self.last-self.first
            self.command('moveto',max(0,min(1-span,self.drag[1]+(pos-self.drag[0])/travel*(1-span))))
    def release(self,e):self.drag=None;self.animate(0)
    def dispose(self,e):
        if e.widget is self and self.job is not None:self.after_cancel(self.job);self.job=None
