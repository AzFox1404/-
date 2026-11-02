# Instructions for project agents

## Start here — keep work focused

Repository: `https://github.com/AzFox1404/-`, branch `main`.
This directory is the user's working checkout. The repository is the source of code history; `Рабочая папка ИД/` is private runtime data, not source code.

Read `docs/PROJECT_MAP.md` and `docs/STATUS.md` first. For performance/preview/save work use `docs/HYBRID_EDITOR.md`, not another broad investigation. Read `docs/REQUIREMENTS.md` only for affected behaviour. Search the relevant module/function with `rg`; do not repeatedly scan client directories, run OCR, export all PDFs or reread the entire development history.

## Sync contract

The user authorized publishing project code to this repository and maintaining this PC copy through GitHub for subsequent work. Follow `docs/SYNC.md` before and after each requested code change.

1. Check local status and remote `main` before editing. Preserve local edits; never overwrite uncommitted work or the runtime data directory with a reset/clean.
2. Bring in remote changes and resolve overlaps. Do not force-push or replace another person's commits.
3. Make and validate the scoped change. Commit and publish; verify remote head, then leave this working copy synchronized to that exact commit.
4. The GitHub connector is authenticated. HTTPS Git currently has no local credential configured. Use connector tree/blob/commit/ref APIs when needed; do not read/extract connector tokens, start an authentication flow implicitly, or claim `git push` succeeded when only an API upload happened.
5. Use `tools/github_bundle.py` for canonical staged blobs and verified local adoption of an API-created commit. Ref updates must use the inspected previous head as `expected_sha`, `force=false`.

There is no background folder watcher. Synchronization occurs while handling an authorized task, not by continuously polling the user's disk. No unattended upload of user projects/documents.

## Product invariants

- Keep source forms, merges, captions, typography and date notation. Small parenthesized captions are explanatory, not fields.
- Recognize known rules first; unknown forms need explicit confirmed bindings. Word and Excel have separate logic.
- PDF colours are review-only; save/export/print are clean. Structural changes mark totals, not shifted text.
- Preserve text and view state when hiding panels. Additional windows work in fullscreen; the application never remains globally topmost.
- Never block Tk with Office, OCR, PDF rendering, a thread join or a synchronous worker wait.
- Pane drag must release mouse capture over glass, the line, original controls, Escape, unmap, focus loss and destruction. Preserve the regression checks for these routes.
- Edit only recovery working copies. Rename a source by remapping its live session and journal; never stop/reopen or save fields merely to rename. Keep immutable project-opening baseline separate from document-save checkpoints. Document discard also restores its last confirmed filename; cancel-exit retains the draft. Whole-project discard restores that baseline, including names and already confirmed per-document saves. Preserve the Excel/Word transaction regression tests.
- Keep at most two warm Office sessions; emit clean PDF before coloured review. Do not mark repeated identical values as edits.
- Queue registry mutations before waiting for PDF; first-position insertion is before the selected first row. Renumber sections without counting headings.
- User documents and original sample folders must never be modified by tests. Use temporary copies.

## Checks and packaging

Run `python tools/check_project.py` first. Then only relevant `verify_*.py`; see `docs/DEVELOPMENT.md`. Office/UI checks are Windows-only and may require private sample files. Do not run every expensive test for a documentation-only change.

Runtime modules and PowerShell workers live together in `app/`; ROOT is the project directory, APP_DIR is the runtime directory. Launch regressions with `python tools/run_check.py verify_name.py` from the project root. Do not scan or execute every test.

Do not publish `.project-local.json`, `.local_notes`, user projects, working copies, OCR caches, source templates, screenshots or personal investigation notes. Existing ignored Russian rules/history files remain local references when a specific case requires them. Do not replace those user files with Git versions.

Record significant changes in `docs/STATUS.md`/`docs/CHANGELOG.md`; update the module map when adding or moving responsibilities. Current EXE packaging is pending; include the isolated PDF worker and review dependency licenses before distribution.

Fast preview is Canvas-only, unique-anchor and fit checked. Never publish it or cache it as final. Final exports must pass formula validation and snapshot SHA matching. Use only verified environment/content keyed final PDFs; never the old print-v1 cache.
