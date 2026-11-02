import tkinter as tk,json,tempfile
from tkinter import ttk
from pathlib import Path
from reportlab.pdfgen import canvas
import studio
from pdf_page_preview import PagePreview
folder=tempfile.TemporaryDirectory();td=Path(folder.name)
studio.STORE=td/'s';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека'/'Шаблоны'
root=tk.Tk();app=studio.Studio(root);root.withdraw()
top=tk.Toplevel(root);top.title('Проверка Ctrl Бюро ИД 3');top.geometry('800x700+70+70')
a=ttk.Entry(top);a.pack(fill='x',padx=12,pady=10);b=ttk.Combobox(top);b.pack(fill='x',padx=12,pady=10)
pdf=td/'text.pdf';c=canvas.Canvas(str(pdf),pagesize=(500,400));c.setFont('Helvetica',20);c.drawString(50,320,'Certificate 869');c.save()
v=PagePreview(top,app);v.pack(fill='both',expand=True);v.show(pdf,0);app.paint(top)
log=[]
def event(e):log.append(dict(code=e.keycode,sym=e.keysym,state=e.state))
for w in (a,b,v.canvas):
 w.bindtags(('LogKeys',)+w.bindtags())
root.bind_class('LogKeys','<KeyPress>',event)
command=Path('review/clipboard-ui-command.json');result=Path('review/clipboard-ui-state.json')
command.unlink(missing_ok=True)
def poll():
 if command.exists():
  try:data=json.loads(command.read_text('utf-8-sig'))
  except (ValueError,OSError):root.after(100,poll);return
  command.unlink()
  if data.get('close'):top.destroy();app.close();folder.cleanup();return
  w={'entry':a,'combo':b,'pdf':v.canvas}[data['focus']]
  if data['focus']=='pdf':
   p=v.selection.pages[0];s=''.join(c for c,box in p['chars']);i=s.index('869');first=p['chars'][i][1];last=p['chars'][i+2][1]
   v.selection.anchor=(p['x']+first[0]*p['w'],p['y']+(first[1]+first[3])/2*p['h']);v.selection.end=(p['x']+last[2]*p['w'],v.selection.anchor[1]);v.selection.highlight()
  else:
   w.delete(0,'end');w.insert(0,data.get('text',''));w.selection_range(0,'end')
  w.focus_force()
 try:clip=root.clipboard_get()
 except tk.TclError:clip=''
 result.write_text(json.dumps(dict(entry=a.get(),combo=b.get(),clipboard=clip,selection=v.selection.text,focus=str(root.focus_get()),events=log[-12:]),ensure_ascii=False),'utf-8')
 root.after(100,poll)
a.insert(0,'Проверка 869');a.selection_range(0,'end');a.focus_force();poll()
root.after(180000,lambda:app.close());root.mainloop()
