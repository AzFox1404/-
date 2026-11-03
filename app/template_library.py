"""Categorized local templates; preserve collisions and unknown user files."""
from pathlib import Path
import shutil

CATEGORIES=('Титулы','АОСР','АООК','Приложения','Реестры','Приказы')
def category(name):
    text=name.casefold()
    for token,folder in [('прилож','Приложения'),('титул','Титулы'),('аоср','АОСР'),('аоок','АООК'),('аоск','АООК'),('реестр','Реестры'),('приказ','Приказы')]:
        if token in text:return folder
    return 'Прочие'

def organize(root,seed=None):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    for folder in CATEGORIES:(root/folder).mkdir(exist_ok=True)
    for path in list(root.rglob('*')):
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or path.suffix.lower() not in ('.doc','.docx','.xls','.xlsx'):continue
        folder=category(path.name)
        if path.parent==root/folder:continue
        target=root/folder/path.name;target.parent.mkdir(exist_ok=True)
        if target.exists():
            if target.read_bytes()==path.read_bytes():path.unlink();continue
            i=2
            while target.exists():target=root/folder/f'{path.stem} ({i}){path.suffix}';i+=1
        path.rename(target)
    # Remove only empty legacy containers inside this library.
    for path in sorted(root.rglob('*'),key=lambda p:len(p.parts),reverse=True):
        if path.is_dir() and not path.is_symlink() and path.resolve().is_relative_to(root.resolve()) and (path.parent!=root or path.name not in (*CATEGORIES,'Прочие')):
            try:path.rmdir()
            except OSError:pass
    if seed and Path(seed).is_dir():
        for path in Path(seed).rglob('*'):
            if path.is_file() and path.suffix.lower() in ('.doc','.docx','.xls','.xlsx'):
                target=root/category(path.name)/path.name;target.parent.mkdir(exist_ok=True)
                if not target.exists():shutil.copy2(path,target)
