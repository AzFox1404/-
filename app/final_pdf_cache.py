"""Only Office-confirmed PDFs; exact source bytes, environment and PDF integrity."""
import hashlib,json,os,locale,re
from pathlib import Path
from functools import lru_cache
from io import BytesIO
from zipfile import ZipFile,BadZipFile
from pypdf.errors import PdfReadError
from app_paths import DATA_DIR

POLICY='bureau-office-clean-v3'

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def printer():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows NT\CurrentVersion\Windows') as key:return winreg.QueryValueEx(key,'Device')[0]
    except (ImportError,OSError):return ''

@lru_cache(maxsize=1)
def environment():
    parts=[POLICY,str(locale.getlocale()),os.environ.get('BUREAU_ID_PDF_PROFILE','')]
    for directory in [Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts']:
        if directory.exists():
            for p in sorted(directory.iterdir()):
                if p.is_file():parts.append((p.name,p.stat().st_size,p.stat().st_mtime_ns))
    for base in ('PROGRAMFILES','PROGRAMFILES(X86)'):
        for name in ('WINWORD.EXE','EXCEL.EXE'):
            for folder in ('Microsoft Office/root/Office16','Microsoft Office/Office16'):
                p=Path(os.environ.get(base,'C:/Program Files'))/folder/name
                if p.exists():parts.append((str(p),p.stat().st_size,p.stat().st_mtime_ns))
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows NT\CurrentVersion\Windows') as key:parts.append(winreg.QueryValueEx(key,'Device')[0])
    except (ImportError,OSError):pass
    return hashlib.sha256(json.dumps(parts,ensure_ascii=False).encode()).hexdigest()

def stable_document(path):
    # Dynamic external/time-dependent fields must be recalculated by Office.
    if path.suffix.lower() not in ('.xlsx','.docx'):return False
    with ZipFile(path) as z:
        for n in z.namelist():
            if n.startswith('xl/externalLinks/'):return False
            if n.startswith(('xl/worksheets/','word/')) and n.endswith('.xml'):
                text=z.read(n).decode('utf-8')
                if path.suffix.lower()=='.xlsx' and re.search(r'\b(NOW|TODAY|RAND|RANDBETWEEN|CELL|INFO)\s*\(',text,re.I):return False
                if ('instrText' in text or 'fldSimple' in text) and re.search(r'\b(DATE|TIME|FILENAME|INCLUDETEXT|INCLUDEPICTURE|LINK|DDE|MERGEFIELD)\b',text,re.I):return False
    return True

class FinalPDFCache:
    def __init__(self,directory=None):self.directory=Path(directory or os.environ.get('BUREAU_ID_PDF_CACHE') or DATA_DIR/'Кэш PDF')
    def key(self,path,source_hash):
        fonts=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'
        stamp=str(fonts.stat().st_mtime_ns) if fonts.exists() else ''
        return hashlib.sha256((source_hash+'|'+Path(path).name+'|'+environment()+'|'+printer()+'|'+stamp+'|'+os.environ.get('BUREAU_ID_PDF_PROFILE','')).encode()).hexdigest()
    def get(self,path):
        try:
            if not self.directory.is_dir():return
            key=self.key(path,digest(path));meta=json.loads((self.directory/(key+'.json')).read_text('utf-8'));pdf=(self.directory/(key+'.pdf')).read_bytes()
            if not isinstance(meta,dict):return
            if meta['verified'] and meta['key']==key and meta['pdf_sha256']==hashlib.sha256(pdf).hexdigest():return pdf
        except (OSError,ValueError,KeyError):pass
    def put(self,path,pdf,expected_hash,errors=()):
        try:
            path=Path(path)
            if errors or not expected_hash or digest(path)!=expected_hash or not stable_document(path):return False
            from pypdf import PdfReader
            pages=len(PdfReader(BytesIO(pdf)).pages)
            if not pages:return False
            key=self.key(path,expected_hash);self.directory.mkdir(parents=True,exist_ok=True)
            import uuid
            tmp=self.directory/(key+'.'+uuid.uuid4().hex+'.tmp')
            tmp.write_bytes(pdf);tmp.replace(self.directory/(key+'.pdf'))
            meta=dict(key=key,verified=True,source_sha256=expected_hash,pdf_sha256=hashlib.sha256(pdf).hexdigest(),pages=pages,policy=POLICY)
            tmp.write_text(json.dumps(meta),'utf-8');tmp.replace(self.directory/(key+'.json'))
            # Bounded disk cache; only our own hash-named entries are retired.
            entries=sorted(self.directory.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
            for old in entries[128:]:
                if re.fullmatch('[0-9a-f]{64}',old.stem):old.with_suffix('.pdf').unlink(missing_ok=True);old.unlink(missing_ok=True)
            return True
        except (OSError,ValueError,KeyError,BadZipFile,PdfReadError,EOFError):return False
