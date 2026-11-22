"""Typed page ranges preserve the remainder and the selected card's metadata."""
import hashlib
import tempfile
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from pypdf import PdfReader
from reportlab.pdfgen import canvas

import scanner_ui
import studio
from pdf_page_preview import PagePreview
from test_pdf_wait import wait_pdf


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def pump(root, seconds=.15):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        root.update();time.sleep(.005)


with tempfile.TemporaryDirectory() as directory:
    folder=Path(directory);source=folder/'source.pdf'
    pdf=canvas.Canvas(str(source),pagesize=(450,600))
    for page in range(1,14):
        pdf.drawString(40,550,f'PAGE {page}');pdf.showPage()
    pdf.save();original=hashlib.sha256(source.read_bytes()).hexdigest()
    records=[dict(path=str(source),source=source.name,start=a,end=b,type='Документ',number='',date='',material='',pages=['']*13)
             for a,b in ((1,5),(6,8),(9,13))]
    scanner_ui.inspect=lambda *args:records
    errors,dialogs,saved=[],[],[]
    scanner_ui.messagebox.showerror=lambda *args,**kwargs:dialogs.append(args)
    scanner_ui.messagebox.showinfo=lambda *args,**kwargs:None
    scanner_ui.messagebox.askyesno=lambda *args,**kwargs:True
    studio.STORE=folder/'store';studio.PROJECTS=studio.STORE/'Projects';studio.LIB=studio.STORE/'Library';studio.SAMPLES=folder/'absent/sample'
    root=tk.Tk();app=studio.Studio(root)
    root.report_callback_exception=lambda *args:errors.append(str(args[1]))
    app.store_passports=lambda output,metadata:saved.append((output,metadata))
    try:
        scanner_ui.scanner(app,files=[source],destination=folder/'out');pump(root,.8)
        win=app.active_scan
        preview=next(w for w in descendants(win) if isinstance(w,PagePreview))
        listing=next(w for w in descendants(win) if isinstance(w,tk.Listbox))
        buttons={w.hint_message:w for w in descendants(win) if hasattr(w,'hint_message')}
        def entry(label):
            heading=next(w for w in descendants(win) if isinstance(w,ttk.Label) and w.cget('text')==label)
            siblings=heading.master.winfo_children();return siblings[siblings.index(heading)+1]
        def edit(label,value):
            widget=entry(label);widget.delete(0,'end');widget.insert(0,value)
        def invoke(label):
            widget=buttons[label];widget.event_generate('<ButtonPress-1>',x=10,y=10);widget.event_generate('<ButtonRelease-1>',x=10,y=10);pump(root)
        def select(index):
            listing.selection_clear(0,'end');listing.selection_set(index);listing.event_generate('<<ListboxSelect>>');pump(root);wait_pdf(root,preview)
        cut='Разделить перед текущей страницей'
        wait_pdf(root,preview)
        for label,value in [('По страницу','1'),('Название документа','Сертификат качества'),('Номер','CERT-1'),('Дата документа','01.11.2026'),('Материал','Steel')]:edit(label,value)
        invoke(cut);wait_pdf(root,preview)
        assert [(r['start'],r['end']) for r in records]==[(1,1),(2,5),(6,8),(9,13)]
        assert records[0]['number']=='CERT-1' and records[0]['material']=='Steel'
        assert '1–1' in listing.get(0) and 'Сертификат качества CERT-1' in listing.get(0)
        assert listing.curselection()==(0,) and preview.page_range==(0,1) and len(preview.pages)==1
        invoke(cut);assert len(records)==4  # Repeated click does not create another remainder.
        select(1);assert len(preview.pages)==4 and records[1]['number']==''
        edit('С первой страницы','3');edit('По страницу','4');edit('Номер','CERT-34')
        invoke(cut);wait_pdf(root,preview)
        assert [(r['start'],r['end']) for r in records]==[(1,1),(2,2),(3,4),(5,5),(6,8),(9,13)]
        assert listing.curselection()==(2,) and preview.page_range==(2,4)
        assert records[2]['number']=='CERT-34' and records[1]['number']==records[3]['number']==''
        # An overlapping range fails without changing any card or its metadata.
        snapshot=[dict(r) for r in records]
        edit('По страницу','5');edit('Номер','SHOULD-NOT-COMMIT');invoke(cut)
        assert dialogs and records==snapshot,(dialogs,records)
        dialogs.clear();edit('По страницу','4');edit('Номер','CERT-34')
        # Switching cards after a range edit must use the clicked card, not its old list index.
        select(4);edit('По страницу','6');edit('Номер','CERT-6');select(5)
        assert entry('С первой страницы').get()=='9' and preview.page_range==(8,13)
        assert [(r['start'],r['end']) for r in records]==[(1,1),(2,2),(3,4),(5,5),(6,6),(7,8),(9,13)]
        select(0);assert entry('Номер').get()=='CERT-1'
        select(6);edit('По страницу','9');edit('Номер','CERT-9')
        # Save applies a typed range too, retaining 10-13 without requiring scissors first.
        invoke('Сохранить отмеченные документы отдельными PDF')
        until=time.monotonic()+15
        while not saved and time.monotonic()<until:pump(root,.05)
        assert saved and len(saved[0][1])==8,(saved,dialogs)
        output,metadata=saved[0]
        for item in metadata:
            pages=PdfReader(output/item['file']).pages
            assert [p.extract_text().strip() for p in pages]==[f'PAGE {n}' for n in range(item['start'],item['end']+1)]
        assert metadata[0]['number']=='CERT-1' and metadata[2]['number']=='CERT-34' and metadata[4]['number']=='CERT-6'
        assert metadata[6]['number']=='CERT-9' and (metadata[7]['start'],metadata[7]['end'])==(10,13)
        assert hashlib.sha256(source.read_bytes()).hexdigest()==original
        assert not errors and not dialogs,(errors,dialogs)
    finally:root.destroy()

print('PASS typed ranges retain both remainders, metadata, correct selection, atomic validation and all 13 saved pages')
