import os
from pathlib import Path

MODEL = os.getenv("AGENT_MODEL", "qwen3:4b")      # для демо: AGENT_MODEL=qwen3:8b
NUM_CTX = int(os.getenv("AGENT_CTX", "8192"))
NUM_THREAD = int(os.getenv("AGENT_THREADS", "4"))  # = физические ядра
APPROVAL = os.getenv("AGENT_APPROVAL", "auto")     # auto | ask
HEADLESS = os.getenv("AGENT_HEADLESS", "0") == "1"
MAX_STEPS = 40
MAX_OUT = 2000                                     # обрезка вывода инструментов

SLOW_MO = int(os.getenv("AGENT_SLOWMO", "0")) 
HOME = Path(os.getenv("AGENT_HOME", Path.home() / ".local-agent"))
MEMORY_DIR = HOME / "memory"
SKILLS_DIRS = [Path(__file__).parent / "skills", HOME / "skills", Path.cwd() / ".agent" / "skills"]
INSTRUCTION_FILES = ["AGENT.md", "CLAUDE.md"]      # аналог CLAUDE.md
