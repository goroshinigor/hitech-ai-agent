"""Все вызовы инструментов проходят через approver.check().
Сейчас используется AutoApprove; режим с подтверждением уже готов (AskUser)."""
from rich.prompt import Confirm


class AutoApprove:
    def check(self, name: str, args: dict) -> bool:
        return True


class AskUser:
    def check(self, name: str, args: dict) -> bool:
        return Confirm.ask(f"[yellow]Разрешить {name}?[/]", default=True)


def get_approver(mode: str):
    return AskUser() if mode == "ask" else AutoApprove()
