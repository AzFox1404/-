"""Inline appendix values retain word spacing and an independent postal address."""
import json,subprocess,tempfile
from pathlib import Path
from docx import Document
from word_fields import analyze_word
from app_paths import APP_DIR

with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    for index,line in enumerate(('к Акту  от    освидетельствования скрытых работ  \u00a0по адресу: ',
                                'к Акту № 1 от 12.03.2025 освидетельствования скрытых работ «Работы» на объекте «Здание» по адресу: Старый адрес')):
        source=root/f'source{index}.docx';prepared=root/f'work{index}.docx'
        document=Document();document.add_paragraph('Реестр документов качества № ');document.add_paragraph(line);document.save(source)
        fields=analyze_word(source,prepared)['fields']
        assert 'regAddress' in fields
        if index:assert fields['regObject']['value']=='«Здание»' and fields['regAddress']['value']=='Старый адрес'
        mapping=root/'map.json';mapping.write_text(json.dumps(fields),encoding='utf-8')
        values=dict(actRef='3487',refDate='13.04.2026',refWork='Монтаж',regAddress='г. Москва',qualityNumber='23')
        requests=[]
        for revision,update in enumerate((values,{k:'' for k in values},values)):
            requests.append(json.dumps(dict(values=update,pdf=str(root/f'{index}-{revision}.pdf'))))
        result=subprocess.run(['powershell.exe','-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',str(APP_DIR/'PreviewWorker.ps1'),'-WorkFile',str(prepared),'-FieldMap',str(mapping)],input='\n'.join(requests)+'\n',capture_output=True,encoding='utf-8',timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
        messages=[json.loads(line.lstrip('\ufeff')) for line in result.stdout.splitlines() if line.strip()]
        assert result.returncode==0 and not any('error' in m for m in messages),(result.stderr,messages)
        saved=Document(prepared)
        assert saved.paragraphs[0].text=='Реестр документов качества №23',repr(saved.paragraphs[0].text)
        printed=saved.paragraphs[1].text
        if index:assert '№3487 от' in printed,repr(printed)
        assert '  ' not in printed and '\u00a0' not in printed,repr(printed)
        assert '3487 от 13.04.2026 освидетельствования' in printed,repr(printed)
        assert 'по адресу: г. Москва' in printed,repr(printed)
        assert ('работ «Монтаж» ' if index else 'работ Монтаж ') in printed,repr(printed)
print('PASS blank/filled appendix: independent address, one space, clear and refill through Word')
