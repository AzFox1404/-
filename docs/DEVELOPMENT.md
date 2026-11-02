# Разработка и проверки

## Среда

Windows x64, Python 3.11+ (с Tk), Office Word/Excel. Установка — `requirements.txt`, для генерации синтетических тестовых PDF — дополнительно `requirements-dev.txt`. В `docs/tested_environment.json` записаны версии проверенной локальной среды, а не обязательная конфигурация каждого ПК.

Рабочие каталоги создаются программой, а не поставляются в Git. `.project-local.json` может содержать `{"examples_root": "D:/MySamples"}`; этот файл игнорируется. Переменные `BUREAU_ID_DATA_DIR` / `BUREAU_ID_EXAMPLES_DIR` переопределяют пути. Не переносите туда токены.

## Быстро

```powershell
python tools/check_project.py
```

Проверяются синтаксис Python/PowerShell, JSON и комплектность исходников. Не запускаются GUI, OCR, Office, полный скан папок и тяжёлый набор интеграционных тестов.

Выбранную проверку из `tests/` запускать так: `python tools/run_check.py verify_home_drag_release.py`. Среда импортов и рабочая папка выставляются автоматически.

## Выбор регрессии по задаче

| Изменение | Проверка |
|---|---|
| Смешанный редактор / итоговый кэш / сборка | `verify_fast_preview.py`, `verify_final_pipeline.py`, `verify_export_snapshot.py`, `verify_make_registry.py`; правила в `docs/HYBRID_EDITOR.md` |
| Переименование / сохранение / скорость переключения | `verify_rename_transaction.py` (Excel), `verify_word_transaction.py` (Word), `verify_journal_baseline.py` |
| Захват мыши/стекло | `verify_home_drag_release.py`, `verify_glass_resize.py` |
| Асинхронный PDF/автопрокрутка/fullscreen | `verify_async_pdf.py` |
| Символы, повороты, OCR, вставка | `verify_pdf_selection.py` (Windows OCR, временные синтетические документы) |
| Сканер/разделение | `verify_scan_checklist.py`, `verify_scan_split.py` |
| Нижняя панель ОС / подсказки | `verify_taskbar_hints.py` (виртуальные координаты; без движения мыши пользователя) |
| Ленты/вспомогательные окна | `verify_utility_controls.py` |
| Панели/полнота иконок | `verify_panel_fit.py`, `verify_panel_preservation.py` (Office + собственные примеры) |
| Реестр: очередь, первая позиция | `verify_row_queue_and_panels.py` (Excel + собственный общий реестр), `verify_word_first_row.py` (Word + собственное приложение) |
| Суммы/временные отметки | `verify_review_and_counts.py`, `verify_structural_review.py` (Office + примеры) |
| Удаление/восстановление | `verify_delete_rows.py`, `verify_register_recovery.py` |

Часть старых `verify_*` — диагностические сценарии ручного тестирования. Они могут ждать ввода и зависеть от названий локальных образцов. Не запускать весь набор автоматически. Сначала читать выбранный файл. Скрипты работают с временными копиями; пользовательские оригиналы не изменять.

## Ограничения реализации

- Tk — только в главном потоке. PDF работает отдельным процессом; Office — через управляемый PowerShell worker.
- `PreviewWorker.ps1` подключает `ActFlow.ps1`, `RegisterRows.ps1`, `WordFields.ps1`, `ReviewHighlight.ps1` относительно `$PSScriptRoot`.
- Проверенные карты Excel дополнены обезличенными якорями `data/act_anchors.json`. Они не содержат заполненных полей и не заменяют проверку неизвестной формы.
- Модули Python и связанные PowerShell workers находятся в `app/`. `ROOT` указывает на корень проекта, `APP_DIR` — на `app/`; данные и vendor остаются в корне.
- EXE пока не собирается. Для упаковки нужны режим отдельного PDF worker, ресурсы TkDND, PowerShell-скрипты, зависимости и проверка условий распространения.

Результат проверки фиксировать в `docs/CHANGELOG.md`; не выдавать успех синтаксиса за визуальную проверку произвольных документов.
