"""Цикл агента: модель -> tool_calls -> выполнение -> результат обратно в модель."""
import json
import ollama
from rich.markdown import Markdown
from rich.panel import Panel
from config import MODEL, NUM_CTX, NUM_THREAD, MAX_STEPS
from tools import REGISTRY, schemas, cut


def compact(messages, keep=8):
    """Старые результаты инструментов ужимаем, чтобы не забить контекст."""
    for m in messages[1:-keep]:
        if isinstance(m, dict) and m.get("role") == "tool" and len(m["content"]) > 300:
            m["content"] = m["content"][:300] + "...[сжато]"


def run(task, messages, console, approver):
    messages.append({"role": "user", "content": task})
    for _ in range(MAX_STEPS):
        compact(messages)
        with console.status("[cyan]думаю...[/]"):
            resp = ollama.chat(model=MODEL, messages=messages, tools=schemas(), think=False,
                               options={"num_ctx": NUM_CTX, "num_thread": NUM_THREAD, "temperature": 0.2})
        msg = resp.message
        messages.append(msg)
        if msg.content:
            console.print(Markdown(msg.content))
        if not msg.tool_calls:
            return
        for call in msg.tool_calls:
            name, args = call.function.name, dict(call.function.arguments)
            console.print(Panel(json.dumps(args, ensure_ascii=False)[:400], title=f"[bold magenta]🔧 {name}[/]", border_style="magenta"))
            if name not in REGISTRY:
                result = f"ERROR: unknown tool {name}"
            elif not approver.check(name, args):
                result = "User denied this action."
            else:
                try:
                    result = str(REGISTRY[name][0](**args))
                except Exception as e:
                    result = f"ERROR: {type(e).__name__}: {e}"
            style = "red" if result.startswith("ERROR") else "green"
            console.print(f"[{style}]{cut(result, 500)}[/]")
            messages.append({"role": "tool", "tool_name": name, "content": result})
    console.print("[yellow]Достигнут лимит шагов.[/]")
