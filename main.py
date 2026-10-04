"""Запуск:  python main.py            (интерактивно)
           python main.py "задача"    (одна задача и выход)"""
import sys
from rich.console import Console
from rich.prompt import Prompt
from approver import get_approver
from config import APPROVAL, MODEL
from context import build_system_prompt, find_skills
from agent import run

console = Console()


def main():
    approver = get_approver(APPROVAL)
    messages = [{"role": "system", "content": build_system_prompt()}]
    console.print(f"[bold cyan]local-agent[/] модель=[green]{MODEL}[/] режим=[yellow]{APPROVAL}[/] скилы={list(find_skills())}")
    if len(sys.argv) > 1:
        return run(" ".join(sys.argv[1:]), messages, console, approver)
    while True:
        try:
            task = Prompt.ask("[bold blue]>[/]").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if task in ("/exit", "/quit"):
            break
        if task == "/clear":
            messages = [{"role": "system", "content": build_system_prompt()}]
            console.print("[dim]контекст очищен[/]")
        elif task:
            run(task, messages, console, approver)


if __name__ == "__main__":
    main()
