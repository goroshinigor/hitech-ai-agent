"""Сборка системного промпта: инструкции проекта, скилы, память."""
import os
import platform
from pathlib import Path
from config import INSTRUCTION_FILES, MEMORY_DIR, SKILLS_DIRS

BASE = """You are a coding agent working in a terminal. OS: {os}. Working dir: {cwd}.
Complete the user's task end-to-end on your own, using tools. Do not ask for confirmation.
Rules:
- Explore first (glob, grep, read_file), then act. Prefer edit_file over rewriting files.
- Keep tool output small. After changes, verify them (run code/tests).
- For tasks with 3+ steps, call load_skill('planning') first. After writing code, call load_skill('self-check').
- Save durable facts about the user/project with memory_save.
- Reply in the user's language. When finished, give a short summary."""


def parse_skill(path: Path):
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        for line in fm.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    return meta, body.strip()


def find_skills() -> dict:
    found = {}
    for d in SKILLS_DIRS:
        for f in sorted(d.glob("*/SKILL.md")) if d.exists() else []:
            meta, _ = parse_skill(f)
            found[meta.get("name", f.parent.name)] = (meta.get("description", ""), f)
    return found


def memory_index() -> str:
    if not MEMORY_DIR.exists():
        return ""
    lines = []
    for f in sorted(MEMORY_DIR.glob("*.md")):
        first = f.read_text(encoding="utf-8").strip().splitlines()[:1]
        lines.append(f"- {f.stem}: {first[0][:100] if first else ''}")
    return "\n".join(lines)


def build_system_prompt() -> str:
    cwd = Path(os.getcwd())
    parts = [BASE.format(os=platform.system(), cwd=cwd)]
    for name in INSTRUCTION_FILES:
        p = cwd / name
        if p.exists():
            parts.append(f"## Project instructions ({name})\n{p.read_text(encoding='utf-8')[:4000]}")
            break
    skills = find_skills()
    if skills:
        parts.append("## Skills (load with load_skill)\n" + "\n".join(f"- {n}: {d}" for n, (d, _) in skills.items()))
    mem = memory_index()
    if mem:
        parts.append("## Memory (read with memory_read)\n" + mem)
    return "\n\n".join(parts)
