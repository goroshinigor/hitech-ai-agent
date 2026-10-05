"""Мини-бенчмарк: прогоняет агента на небольшом наборе задач с автопроверкой.
   python bench.py                  все задачи (кроме браузера)
   python bench.py --only 1,3       только выбранные
   python bench.py --browser        добавить тест браузера
   python bench.py --timeout 900    лимит на задачу, сек
Результат: таблица в консоли + bench_report.md + логи в bench_logs/"""
import argparse
import datetime
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from rich.console import Console
from rich.table import Table
from config import MODEL, NUM_CTX, NUM_THREAD

ROOT = Path(__file__).parent
console = Console()


def py(cwd, code):
    r = subprocess.run([sys.executable, "-c", code], cwd=cwd, capture_output=True, text=True, timeout=30)
    return r.returncode, (r.stdout + r.stderr).strip()


def tail(out, n=400):
    return out[-n:]


# ---------- подготовка ----------
def s_none(d): pass


def s_calc(d):
    (d / "calc.py").write_text("def add(a, b):\n    return a + b\n\ndef div(a, b):\n    return a / b\n")


def s_search(d):
    (d / "mod_a.py").write_text("def helper():\n    return 1\n")
    (d / "mod_b.py").write_text("def secret_function():\n    return 42\n")
    (d / "mod_c.py").write_text("def other():\n    return 3\n")


def s_delete(d):
    (d / "delete_me.txt").write_text("bye\n")


def s_instr(d):
    (d / "AGENT.md").write_text("Always end every .py file you create with the comment line: # checked-by-agent\n")


# ---------- проверки: (ok, заметка) ----------
def c_hello(d, out):
    if not (d / "hello.py").exists():
        return False, "нет hello.py"
    rc, o = py(d, "import runpy; runpy.run_path('hello.py')")
    return o.split() == [str(i) for i in range(1, 11)], "вывод: " + o[:60].replace("\n", " ")


def c_prime(d, out):
    if not (d / "prime.py").exists() or not (d / "test_prime.py").exists():
        return False, "нет prime.py или test_prime.py"
    rc, o = py(d, "from prime import is_prime as p\nassert p(2) and p(17) and p(97)\nassert not (p(0) or p(1) or p(15) or p(100))\nprint('ok')")
    return rc == 0, o[-80:]


def c_plan(d, out):
    plan = d / "PLAN.md"
    if not plan.exists():
        return False, "нет PLAN.md"
    t = plan.read_text(encoding="utf-8").lower()
    if "[x]" not in t or "[ ]" in t:
        return False, "в плане остались невыполненные пункты"
    rc, o = py(d, "import calc\nassert calc.add(2,3)==5 and calc.sub(5,3)==2 and calc.mul(2,3)==6 and calc.div(6,3)==2\nprint('ok')")
    return rc == 0, o[-80:]


def c_edit(d, out):
    code = ("import calc\nassert calc.div(6,3)==2\n"
            "try:\n    calc.div(1,0)\nexcept Exception as e:\n"
            "    assert type(e).__name__!='ZeroDivisionError' or str(e) not in ('','division by zero','float division by zero')\n"
            "    print('ok')\nelse:\n    raise SystemExit(1)\n")
    rc, o = py(d, code)
    return rc == 0, o[-80:] or "div(1,0) не выбрасывает ошибку или сообщение стандартное"


def c_search(d, out):
    t = tail(out)
    return "mod_b.py" in t and "mod_a.py" not in t, "конец ответа: " + t[-60:].replace("\n", " ")


def c_delete(d, out):
    return not (d / "delete_me.txt").exists(), ""


def c_instr(d, out):
    f = d / "util.py"
    if not f.exists():
        return False, "нет util.py"
    t = f.read_text(encoding="utf-8")
    rc, o = py(d, "from util import double\nassert double(2)==4\nprint('ok')")
    return rc == 0 and "# checked-by-agent" in t, "комментарий " + ("есть" if "# checked-by-agent" in t else "отсутствует")


def c_memory(d, out):
    mem = d / "home" / "memory"
    hit = [f.name for f in mem.glob("*.md") if "pytest" in f.read_text(encoding="utf-8").lower()] if mem.exists() else []
    return bool(hit), ", ".join(hit) or "заметка не сохранена"


def c_browser(d, out):
    return "browser_goto" in out and "example domain" in out.lower(), ""


TASKS = [
    (1, "Файлы + bash", "Создай файл hello.py, который печатает числа от 1 до 10, и запусти его.", s_none, c_hello),
    (2, "Самопроверка (skill)", "Напиши функцию is_prime(n) в prime.py и тесты к ней в test_prime.py. Запусти тесты и исправь ошибки, если они есть.", s_none, c_prime),
    (3, "Планирование (skill)", "Создай мини-проект: calc.py с функциями add, sub, mul, div. Сначала составь план в PLAN.md и отмечай выполненные пункты.", s_none, c_plan),
    (4, "Правка файла", "В calc.py измени функцию div так, чтобы при делении на ноль выбрасывалась понятная ошибка с сообщением.", s_calc, c_edit),
    (5, "Поиск по проекту", "В каком файле определена функция secret_function? В конце ответа напиши только имя файла.", s_search, c_search),
    (6, "Удаление файла", "Удали файл delete_me.txt.", s_delete, c_delete),
    (7, "Файл инструкций", "Создай util.py с функцией double(x), возвращающей x*2.", s_instr, c_instr),
    (8, "Память", "Запомни: я предпочитаю pytest вместо unittest.", s_none, c_memory),
    (9, "Браузер", "Открой https://example.com и скажи, какой заголовок на странице. Ответь одной строкой.", s_none, c_browser),
]


def run_agent(d, prompt, timeout):
    env = {**os.environ, "AGENT_HOME": str(d / "home"), "AGENT_APPROVAL": "auto",
           "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "NO_COLOR": "1"}
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, str(ROOT / "main.py"), prompt], cwd=d, env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return r.stdout + r.stderr, time.time() - t0, False
    except subprocess.TimeoutExpired:
        return "", time.time() - t0, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--browser", action="store_true")
    a = ap.parse_args()

    try:
        import ollama
        ollama.show(MODEL)
    except Exception as e:
        sys.exit(f"Ollama недоступна или модели {MODEL} нет: {e}")

    only = {int(x) for x in a.only.split(",") if x}
    tasks = [t for t in TASKS if (t[0] in only if only else (t[0] != 9 or a.browser))]
    logs = ROOT / "bench_logs"
    logs.mkdir(exist_ok=True)
    console.print(f"[bold cyan]bench[/] модель=[green]{MODEL}[/] ctx={NUM_CTX} threads={NUM_THREAD} задач={len(tasks)}")

    rows = []
    for n, name, prompt, setup, check in tasks:
        d = Path(tempfile.mkdtemp(prefix=f"bench{n}_"))
        setup(d)
        console.print(f"[yellow]▶ {n}. {name}[/] ...")
        out, secs, timed_out = run_agent(d, prompt, a.timeout)
        (logs / f"{n}.log").write_text(out, encoding="utf-8")
        steps = out.count("🔧")
        if timed_out:
            ok, note = False, f"таймаут {a.timeout}с"
        elif "Traceback" in out:
            ok, note = False, "ошибка: " + out.strip().splitlines()[-1][:80]
        else:
            try:
                ok, note = check(d, out)
            except Exception as e:
                ok, note = False, f"проверка упала: {e}"
        rows.append((n, name, ok, secs, steps, note))
        console.print(("[green]  PASS[/]" if ok else "[red]  FAIL[/]") + f" {secs:.0f}с, шагов {steps}. {note}")

    passed = sum(r[2] for r in rows)
    table = Table(title=f"{MODEL}: {passed}/{len(rows)}")
    for c in ("#", "Задача", "Итог", "Время", "Шагов", "Заметка"):
        table.add_column(c)
    for n, name, ok, secs, steps, note in rows:
        table.add_row(str(n), name, "[green]PASS[/]" if ok else "[red]FAIL[/]", f"{secs:.0f}с", str(steps), note)
    console.print(table)

    md = [f"# Отчёт бенчмарка", f"- Модель: `{MODEL}`, ctx={NUM_CTX}, threads={NUM_THREAD}",
          f"- Дата: {datetime.datetime.now():%Y-%m-%d %H:%M}", f"- Пройдено: **{passed}/{len(rows)}**",
          f"- Общее время: {sum(r[3] for r in rows) / 60:.1f} мин", "",
          "| # | Задача | Итог | Время | Шагов | Заметка |", "|---|---|---|---|---|---|"]
    for n, name, ok, secs, steps, note in rows:
        md.append(f"| {n} | {name} | {'PASS' if ok else 'FAIL'} | {secs:.0f}с | {steps} | {note.replace('|', '/')} |")
    (ROOT / "bench_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    console.print("[dim]отчёт: bench_report.md, логи: bench_logs/[/]")


if __name__ == "__main__":
    main()
