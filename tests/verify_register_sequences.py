from pathlib import Path
from workspace_preview import SAMPLES
import tempfile,shutil,subprocess
with tempfile.TemporaryDirectory() as td:
 p=Path(td);g=p/'general.xlsx';q=p/'quality.xlsx'
 shutil.copy2(SAMPLES.parent/'Реестр.xlsx',g);shutil.copy2(next(SAMPLES.rglob('Реестр документов качества к АОСР №КМ-1.xlsx')),q)
 subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File','review/verify_register_sequences.ps1','-General',str(g),'-Quality',str(q)],check=True)
