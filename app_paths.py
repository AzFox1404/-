"""Shared paths; private data stays outside version control."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
try:
    _local = json.loads((ROOT / '.project-local.json').read_text('utf-8-sig'))
except (OSError, ValueError):
    _local = {}

DATA_DIR = Path(os.environ.get('BUREAU_ID_DATA_DIR') or ROOT / 'Рабочая папка ИД').expanduser().resolve()
_legacy = ROOT.parent / 'ИД здание 1 - 18х48'
EXAMPLES_ROOT = Path(os.environ.get('BUREAU_ID_EXAMPLES_DIR') or _local.get('examples_root') or (_legacy if _legacy.exists() else ROOT / 'examples')).expanduser().resolve()
