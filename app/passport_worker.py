"""One-shot passport analysis process. No Tk or application objects here."""
import json
import sys
from pathlib import Path


def main():
    from passports import inspect
    request=json.loads(Path(sys.argv[1]).read_text('utf-8'))
    def emit(kind,data):
        print(json.dumps([kind,data],ensure_ascii=False),flush=True)
    try:
        records=inspect([Path(p) for p in request['files']],Path(request['tmp']),
                        lambda text:emit('status',text),Path(request['cache']))
        target=Path(request['result'])
        target.write_text(json.dumps(records,ensure_ascii=False),'utf-8')
        emit('ready',None)
    except Exception as exc:
        emit('error',str(exc));return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
