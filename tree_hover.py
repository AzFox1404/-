"""Rounded hover overlay for a tree row. It preserves the tree's click handlers."""
import tkinter as tk

def install(tree):
    state={'row':None,'overlay':None}
    def hide(*_):
        if state['overlay'] is not None:
            state['overlay'].destroy();state['overlay']=None
        state['row']=None
    def motion(e):
        row=tree.identify_row(e.y)
        if not row or row==state['row']:return
        hide();bbox=tree.bbox(row)
        if not bbox:return
        x,y,width,height=bbox
        state['row']=row
        overlay=tk.Canvas(tree,highlightthickness=0,bd=0,height=height,width=max(1,tree.winfo_width()-20),bg=tree.tk.call('ttk::style','lookup','Treeview','-background'))
        state['overlay']=overlay;overlay.place(x=19,y=y,width=max(1,tree.winfo_width()-20),height=height)
        w=max(1,tree.winfo_width()-20);h=height;r=5
        points=[r,0,w-r,0,w,0,w,r,w,h-r,w,h,w-r,h,r,h,0,h,0,h-r,0,r,0,0]
        overlay.create_polygon(points,smooth=True,splinesteps=16,fill='#e8ddd3',outline='')
        overlay.create_text(max(6,x-13),h/2,text=tree.item(row,'text'),anchor='w',fill='black',font=('Segoe UI',9))
        values=tree.item(row,'values')
        if values:overlay.create_text(max(w-108,20),h/2,text=str(values[0]),anchor='w',fill='black',font=('Segoe UI',9))
        def click(e):
            tree.focus_set()
            y=tree.bbox(row)[1]+e.y if tree.bbox(row) else -1
            hide();tree.event_generate('<Button-1>',x=e.x+19,y=y)
        overlay.bind('<Button-1>',click);overlay.bind('<Leave>',hide)
        overlay.bind('<MouseWheel>',lambda e:(hide(),tree.yview_scroll(-3 if e.delta>0 else 3,'units')))
    tree.bind('<Motion>',motion,add='+');tree.bind('<Leave>',lambda e:None,add='+')
    tree.bind('<Configure>',hide,add='+');tree.bind('<MouseWheel>',hide,add='+');tree.bind('<Destroy>',hide,add='+')
    return hide
