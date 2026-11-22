"""Split a continuous 13-page source and save independent certificate cards."""
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


def pump(root, seconds=.12):
    end = time.monotonic()+seconds
    while time.monotonic() < end:
        root.update()
        time.sleep(.005)


with tempfile.TemporaryDirectory() as directory:
    folder = Path(directory)
    source = folder/'certificates.pdf'
    pdf = canvas.Canvas(str(source), pagesize=(450, 600))
    for page in range(1, 14):
        pdf.drawString(40, 550, f'CERTIFICATE PAGE {page}')
        pdf.showPage()
    pdf.save()
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    records = [dict(path=str(source), source=source.name, start=a, end=b,
                    type='Сертификат качества', number=str(a), date='01.11.2026',
                    material='', pages=['']*13)
               for a, b in ((1, 5), (6, 6), (7, 9), (10, 13))]
    scanner_ui.inspect = lambda *args: records
    dialogs, errors, saved = [], [], []
    scanner_ui.messagebox.showerror = lambda *args, **kwargs: dialogs.append(args)
    scanner_ui.messagebox.showinfo = lambda *args, **kwargs: None
    scanner_ui.messagebox.askyesno = lambda *args, **kwargs: True
    studio.STORE = folder/'store'
    studio.PROJECTS = studio.STORE/'Projects'
    studio.LIB = studio.STORE/'Library'
    studio.SAMPLES = folder/'absent/sample'
    root = tk.Tk()
    app = studio.Studio(root)
    root.report_callback_exception = lambda *args: errors.append(str(args[1]))
    app.store_passports = lambda output, metadata: saved.append((output, metadata))
    try:
        scanner_ui.scanner(app, files=[source], destination=folder/'output')
        pump(root, .8)
        win = app.active_scan
        win.geometry('1050x800')
        pump(root)
        preview = next(w for w in descendants(win) if isinstance(w, PagePreview))
        listing = next(w for w in descendants(win) if isinstance(w, tk.Listbox))
        wait_pdf(root, preview)
        preview.set_zoom(130)
        pump(root)
        buttons = {w.hint_message: w for w in descendants(win) if hasattr(w, 'hint_message')}
        def invoke(label):
            widget = buttons[label]
            widget.event_generate('<ButtonPress-1>', x=10, y=10)
            widget.event_generate('<ButtonRelease-1>', x=10, y=10)
            pump(root)
        def entry(label):
            heading = next(w for w in descendants(win) if isinstance(w, ttk.Label) and w.cget('text') == label)
            siblings = heading.master.winfo_children()
            return siblings[siblings.index(heading)+1]
        def fill(page):
            for label, value in [('Название документа', 'Сертификат качества'), ('Номер', f'100{page:02}'), ('Дата документа', f'{page:02}.11.2026'), ('Материал', f'Material {page}')]:
                widget = entry(label)
                widget.delete(0, 'end')
                widget.insert(0, value)
        fill(1)
        for page in range(2, 14):
            # Like the screenshot: the preceding page remains at the top,
            # while the next certificate occupies most of the visible area.
            top = preview.pages[page-1][0]-160
            preview.canvas.yview_moveto(top/preview.height)
            if page != 3:
                pump(root)
            # Page 3 is split immediately, before the delayed preview refresh.
            invoke('Разделить перед текущей страницей')
            assert listing.curselection() == (page-1,), (page, listing.curselection())
            assert entry('С первой страницы').get() == str(page)
            if page not in (6, 7, 10):
                assert entry('Номер').get() == '', (page, entry('Номер').get())
            fill(page)
        assert [(r['start'], r['end']) for r in records] == [(n, n) for n in range(1, 14)]
        invoke('Сохранить отмеченные документы отдельными PDF')
        end = time.monotonic()+15
        while not saved and time.monotonic() < end:
            pump(root, .05)
        assert saved and len(saved[0][1]) == 13, (saved, dialogs)
        output, metadata = saved[0]
        for page, record in enumerate(metadata, 1):
            assert record['number'] == f'100{page:02}' and record['material'] == f'Material {page}', record
            assert record['date'] == f'{page:02}.11.2026', record
            assert record['type'] == 'Сертификат качества', record
            result = PdfReader(output/record['file'])
            assert len(result.pages) == 1
            assert f'CERTIFICATE PAGE {page}' in result.pages[0].extract_text()
        assert hashlib.sha256(source.read_bytes()).hexdigest() == original
        assert not dialogs and not errors, (dialogs, errors)
    finally:
        root.destroy()

print('PASS 13-page continuous split, independent metadata, 13 exact PDFs and unchanged source')
