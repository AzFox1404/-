"""Run one selected regression with application imports and project-relative paths."""
import os,runpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if len(sys.argv)!=2:raise SystemExit('Usage: python tools/run_check.py verify_name.py')
path=(ROOT/'tests'/sys.argv[1]).resolve()
if path.parent!=ROOT/'tests' or not path.is_file():raise SystemExit('Choose one file in tests/')
sys.path[:0]=[str(ROOT/'app'),str(ROOT/'tests')]
os.chdir(ROOT);sys.argv=[str(path)];runpy.run_path(str(path),run_name='__main__')
