"""Isolate native PDF/OCR faults and cancellation from the Tk process."""
import json
import subprocess
import sys
import time
from pathlib import Path


def inspect(files,tmp,notify,cache,cancelled=None):
    request=tmp/'analysis-request.json';result=tmp/'analysis-result.json'
    request.write_text(json.dumps(dict(files=list(map(str,files)),tmp=str(tmp),
                                      cache=str(cache),result=str(result))),'utf-8')
    # Regular files allow cancellation without a blocking pipe readline. They
    # live only in the scanner's temporary directory and never reach Git.
    with (tmp/'analysis-events.jsonl').open('w',encoding='utf-8') as out, \
         (tmp/'analysis-stderr.log').open('w',encoding='utf-8') as err:
        process=subprocess.Popen([sys.executable,'-X','utf8','-u',
                    str(Path(__file__).with_name('passport_worker.py')),str(request)],
                    stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            with (tmp/'analysis-events.jsonl').open(encoding='utf-8') as events:
                ready=False;error=None;last=time.monotonic()
                while True:
                    if cancelled is not None and cancelled.is_set():raise RuntimeError('Анализ отменён')
                    line=events.readline()
                    if line:
                        kind,data=json.loads(line);last=time.monotonic()
                        if kind=='status':notify(data)
                        elif kind=='error':error=data
                        elif kind=='ready':ready=True
                        continue
                    code=process.poll()
                    if code is not None:
                        if error:raise ValueError(error)
                        if code or not ready:
                            raise RuntimeError('Процесс анализа PDF завершился с ошибкой. Исходные файлы сохранены. Код: '+str(code))
                        return json.loads(result.read_text('utf-8'))
                    if time.monotonic()-last>300:raise TimeoutError('Анализ страницы не отвечает более 5 минут. Попробуйте загрузить файл отдельно.')
                    time.sleep(.05)
        finally:
            if process.poll() is None:
                # This PID belongs solely to this job; include its OCR child.
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],
                               capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=15)
            process.wait(timeout=15)
