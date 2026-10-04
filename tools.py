"""Реестр инструментов. Новый инструмент = функция с декоратором @tool."""
import os
import platform
import re
import subprocess
from pathlib import Path
from config import MAX_OUT, MEMORY_DIR, HEADLESS
from context import find_skills, parse_skill

REGISTRY = {}   # name -> (func, json-schema)
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}


def tool(desc, **params):
    """params: имя='описание'; если в описании есть '(optional)' — параметр необязателен."""
    def deco(fn):
        props = {k: {"type": "string", "description": v} for k, v in params.items()}
        req = [k for k, v in params.items() if "(optional)" not in v]
        REGISTRY[fn.__name__] = (fn, {"type": "function", "function": {
            "name": fn.__name__, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": req}}})
        return fn
    return deco


def cut(s: str, n: int = MAX_OUT) -> str:
    return s if len(s) <= n else s[:n] + f"\n...[обрезано, ещё {len(s) - n} симв.]"


def schemas():
    return [s for _, s in REGISTRY.values()]


# ---------- файлы ----------
@tool("Read a text file.", path="file path")
def read_file(path):
    return cut(Path(path).read_text(encoding="utf-8", errors="replace"), 6000)


@tool("Create or overwrite a file.", path="file path", content="full file content")
def write_file(path, content):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"written {len(content)} chars to {path}"


@tool("Replace exactly one occurrence of old with new in a file.", path="file path", old="exact text to find", new="replacement")
def edit_file(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    n = text.count(old)
    if n != 1:
        return f"ERROR: 'old' found {n} times, must be exactly 1. Add more context."
    p.write_text(text.replace(old, new), encoding="utf-8")
    return "edited"


@tool("Delete a file.", path="file path")
def delete_file(path):
    Path(path).unlink()
    return f"deleted {path}"


# ---------- поиск ----------
@tool("Find files by name pattern, e.g. '**/*.py'.", pattern="glob pattern")
def glob(pattern):
    res = [str(p) for p in Path(".").glob(pattern) if not SKIP_DIRS & set(p.parts)]
    return cut("\n".join(res[:200]) or "no matches")


@tool("Search file contents with a regex (like grep -rn).", pattern="regex", path="directory (optional, default .)")
def grep(pattern, path="."):
    rx, out = re.compile(pattern), []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            fp = os.path.join(root, f)
            try:
                for i, line in enumerate(open(fp, encoding="utf-8"), 1):
                    if rx.search(line):
                        out.append(f"{fp}:{i}:{line.strip()[:160]}")
            except (UnicodeDecodeError, OSError):
                continue
            if len(out) >= 100:
                return cut("\n".join(out))
    return cut("\n".join(out) or "no matches")


# ---------- терминал ----------
@tool("Run a shell command and return its output (timeout 120s).", command="shell command")
def bash(command):
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return "ERROR: timeout 120s"
    return cut(f"exit={r.returncode}\n{r.stdout}{r.stderr}")


@tool("Open a NEW terminal window and run a command in it (for long-running processes).", command="shell command")
def open_terminal(command):
    if platform.system() == "Windows":
        subprocess.Popen(["cmd", "/k", command], creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        subprocess.Popen(["x-terminal-emulator", "-e", f"bash -c '{command}; exec bash'"])
    return "terminal opened"


# ---------- браузер (Playwright, запускается лениво) ----------
_pw = {}


def _page():
    if "page" not in _pw:
        from playwright.sync_api import sync_playwright
        _pw["p"] = sync_playwright().start()
        _pw["b"] = _pw["p"].chromium.launch(headless=HEADLESS)
        _pw["page"] = _pw["b"].new_page()
    return _pw["page"]


@tool("Open a URL in the browser and return the page text.", url="full URL")
def browser_goto(url):
    pg = _page()
    pg.goto(url, wait_until="domcontentloaded", timeout=30000)
    return cut(f"{pg.title()}\n{pg.inner_text('body')}")


@tool("List links on the current page.")
def browser_links():
    links = _page().eval_on_selector_all("a[href]", "els => els.slice(0,40).map(e => (e.innerText||'').trim().slice(0,60)+' -> '+e.href)")
    return cut("\n".join(links))


@tool("Click an element by its visible text, then return the page text.", text="visible text")
def browser_click(text):
    pg = _page()
    pg.get_by_text(text).first.click(timeout=10000)
    pg.wait_for_load_state("domcontentloaded")
    return cut(f"{pg.url}\n{pg.inner_text('body')}")


# ---------- память и скилы ----------
@tool("Save a durable note to long-term memory (first line = short summary).", name="short slug", content="note text")
def memory_save(name, content):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    (MEMORY_DIR / f"{re.sub(r'[^\w-]', '_', name)}.md").write_text(content, encoding="utf-8")
    return "saved"


@tool("Read a note from long-term memory.", name="note name from the memory list")
def memory_read(name):
    return cut((MEMORY_DIR / f"{name}.md").read_text(encoding="utf-8"), 4000)


@tool("Load the full instructions of a skill.", name="skill name")
def load_skill(name):
    skills = find_skills()
    if name not in skills:
        return f"unknown skill. available: {', '.join(skills)}"
    return parse_skill(skills[name][1])[1]
