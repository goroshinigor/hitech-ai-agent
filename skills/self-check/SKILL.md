---
name: self-check
description: После написания кода запустить его или тесты, разобрать ошибки и исправить в цикле
---
# Self-check
1. Run the code or tests with `bash` (e.g. `python file.py`, `pytest -x`, `php -l file.php`).
2. If exit code is 0 and output is as expected — done.
3. If it fails: read the LAST lines of the traceback, find the file/line with `read_file`, fix with `edit_file`.
4. Run again. Repeat at most 5 times.
5. If still failing after 5 attempts, stop and report what fails and your best hypothesis.
Never claim success without a run that really passed.
