"""Preliminary canvas edits never alter PDF bytes or claim a full reflow."""
import tempfile,time,tkinter as tk
from pathlib import Path
from reportlab.pdfgen import canvas
from pdf_page_preview import PagePreview
import studio

def pump(root,until,timeout=8):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        root.update();time.sleep(.005)
        if until():return True
    return False

with tempfile.TemporaryDirectory() as td:
    p=Path(td);studio.STORE=p/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны'
    source=p/'test.pdf';c=canvas.Canvas(str(source),pagesize=(500,600));c.setFont('Helvetica',12);c.drawString(50,540,'DOCUMENT-1234');c.drawString(50,500,'Same Name');c.showPage();c.drawString(50,500,'Same Name');c.save()
    before=source.read_bytes();root=tk.Tk();app=studio.Studio(root);top=tk.Toplevel(root);view=PagePreview(top,app);view.pack(fill='both',expand=True)
    view.set_quick_model(dict(number='DOCUMENT-1234',developer='Same Name'),{})
    view.show(source,0)
    assert pump(root,lambda:'number' in view.quick_anchors and bool(view.images))
    assert 'developer' not in view.quick_anchors,'same text on another page is ambiguous'
    count=view.renderer.render_count;t=time.perf_counter();assert view.quick_field('number','DOC-9');elapsed=(time.perf_counter()-t)*1000
    assert view.renderer.render_count==count and source.read_bytes()==before
    # All bound unique text fields can use the same guarded path, not only FIO.
    from fast_preview import eligible
    assert eligible({'address':'DOCUMENT-1234','row9_2':'Unique material'}, {})=={'address':'DOCUMENT-1234','row9_2':'Unique material'}
    for value in ('D','DO','DOC','','D'):
        view.show_draft('number',value,'Номер документа')
        assert view.draft_text.get('1.0','end-1c')==value
        assert view.quick_field('number',value)
    view.show_draft('date','12.0','Дата')
    assert view.field_draft==('date','12.0') and view.draft_area.winfo_manager()=='pack'
    view.clear_draft();assert not view.draft_area.winfo_manager()
    assert view.quick_field('number','DOC-9')
    assert len(view.canvas.find_withtag('quick-edit'))==2 and view.quick_notice.winfo_manager()=='pack'
    assert view.quick_field('number','This string cannot fit into the original field') is False
    assert not view.canvas.find_withtag('quick-edit') and not view.quick_changes
    assert view.quick_field('number','DOC-9');view.set_zoom(125)
    assert pump(root,lambda:bool(view.canvas.find_withtag('quick-edit')))
    view.rotate(90);assert not view.quick_field('number','DOC-8')
    assert source.read_bytes()==before
    view.renderer.close();top.destroy();app.close()
    print(f'PASS unique whole-document anchor, duplicate rejection, instant canvas edit {elapsed:.1f} ms, no PDF mutation/rerender, overflow fallback and rotation guard')
