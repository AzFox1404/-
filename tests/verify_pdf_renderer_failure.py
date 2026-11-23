"""A real renderer import failure reports its cause and permits reopening."""
import tempfile
import time
import tkinter as tk
from pathlib import Path

from reportlab.pdfgen import canvas

import pdf_renderer
import studio
from pdf_page_preview import PagePreview
from test_pdf_wait import wait_pdf


def pump(root, until, timeout=12):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        root.update();time.sleep(.005)
        if until():return
    raise AssertionError('PDF state did not arrive')


with tempfile.TemporaryDirectory() as directory:
    folder=Path(directory);source=folder/'source.pdf'
    pdf=canvas.Canvas(str(source))
    for n in range(1,3):
        pdf.drawString(40,700,f'PAGE {n}');pdf.showPage()
    pdf.save()
    studio.STORE=folder/'store';studio.PROJECTS=studio.STORE/'Projects';studio.LIB=studio.STORE/'Library';studio.SAMPLES=folder/'absent/sample'
    root=tk.Tk();app=studio.Studio(root);errors=[]
    root.report_callback_exception=lambda *args:errors.append(str(args[1]))
    view=PagePreview(root,app);view.pack(fill='both',expand=True);root.update()
    original=pdf_renderer.subprocess.Popen;launches=[]
    def launch(command,**kwargs):
        # -S omits site-packages in this one child only. It reproduces the real
        # missing PyMuPDF failure without uninstalling anything from the PC.
        command=list(command)
        if not launches:command.insert(1,'-S')
        launches.append(command)
        return original(command,**kwargs)
    pdf_renderer.subprocess.Popen=launch
    try:
        view.show(source,0,page_range=(1,2))
        pump(root,lambda:getattr(view,'_load_failed',False))
        assert 'PyMuPDF' in view.selection.message.get(),view.selection.message.get()
        assert 'Ran out of input' not in view.selection.message.get()
        assert 'Загрузка' not in view.page_text.get()
        # The same file and same range can recover, using a newly launched process.
        view.show(source,0,page_range=(1,2));wait_pdf(root,view)
        text=''.join(c for item in view.selection.pages.values() for c,_ in item['chars'])
        assert 'PAGE 2' in text and 'PAGE 1' not in text,text
        assert len(launches)==2 and len(view.pages)==1
        # Contain an actual fatal process exit, then recover without rebuilding the UI.
        view.renderer.process.kill();view.renderer.process.wait(timeout=3)
        view.renderer.page(view._generation,view._epoch,0,view.zoom,0)
        pump(root,lambda:getattr(view,'_load_failed',False))
        assert 'код' in view.selection.message.get()
        view.show(source,0,page_range=(1,2));wait_pdf(root,view)
        assert len(launches)==3 and not errors,errors
    finally:
        pdf_renderer.subprocess.Popen=original
        view.renderer.close();root.destroy()

print('PASS missing dependency diagnosis, loading-state exit, fatal-worker containment and same-range recovery')
