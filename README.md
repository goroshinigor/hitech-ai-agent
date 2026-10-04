# local-agent
Компактный терминальный агент на локальной LLM (Ollama).

    ollama pull qwen3:4b          # для демо: qwen3:8b
    pip install -r requirements.txt
    playwright install chromium
    cd <папка-проекта> && python <путь>/main.py

Переменные: AGENT_MODEL, AGENT_CTX, AGENT_THREADS, AGENT_APPROVAL=auto|ask, AGENT_HEADLESS=1.
Инструкции проекта: AGENT.md или CLAUDE.md в текущей папке. Скилы: skills/<имя>/SKILL.md
(также ~/.local-agent/skills и ./.agent/skills). Память: ~/.local-agent/memory/*.md
