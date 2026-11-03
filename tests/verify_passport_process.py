"""Real text PDF analysis, worker crash containment and cancellation; no user files."""
import tempfile,threading,time
from pathlib import Path
from reportlab.pdfgen import canvas
from passport_process import inspect

with tempfile.TemporaryDirectory() as td:
    p=Path(td);pdf=p/'source.pdf';c=canvas.Canvas(str(pdf))
    for i in range(2):
        c.drawString(30,700,'A long sample document text for native extraction, page '+str(i+1));c.showPage()
    c.save();tmp=p/'work';tmp.mkdir();events=[]
    records=inspect([pdf],tmp,events.append,p/'cache')
    assert records and records[0]['start']==1 and records[-1]['end']==2 and events
    assert all(Path(r['path']).is_file() for r in records)
    from PIL import Image,ImageDraw,ImageFont
    image=Image.new('RGB',(1600,700),'white');draw=ImageDraw.Draw(image)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',58)
    draw.text((70,100),'Сертификат качества № 869',font=font,fill='black')
    draw.text((70,220),'Дата выдачи 14.01.2024',font=font,fill='black')
    scan=p/'scan.jpg';image.save(scan)
    recognized=inspect([scan],tmp,events.append,p/'cache')
    assert recognized[0]['type']=='Сертификат качества',recognized
    assert recognized[0]['number']=='869' and recognized[0]['date']=='14.01.2024',recognized
    bad=p/'bad.pdf';bad.write_bytes(b'broken PDF')
    try:inspect([bad],tmp,events.append,p/'cache')
    except (ValueError,RuntimeError):pass
    else:raise AssertionError('bad PDF must report a recoverable error')
    import passport_process
    native=passport_process.subprocess.Popen
    def crash(*args,**kw):
        return native([__import__('sys').executable,'-c','import os;os._exit(17)'],**kw)
    passport_process.subprocess.Popen=crash
    try:
        try:inspect([pdf],tmp,events.append,p/'cache')
        except RuntimeError as exc:assert '17' in str(exc)
        else:raise AssertionError('worker crash was not reported')
    finally:passport_process.subprocess.Popen=native
    cancelled=threading.Event();cancelled.set();started=time.monotonic()
    try:inspect([pdf],tmp,events.append,p/'cache',cancelled)
    except RuntimeError:pass
    else:raise AssertionError('cancel ignored')
    assert time.monotonic()-started<10
print('PASS isolated native PDF/JPEG OCR, invalid PDF and fatal worker errors, process-tree cancellation')
