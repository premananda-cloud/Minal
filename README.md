# NIELIT Imphal Ambassador Assistant (codename: Minal)

A local, offline AI assistant that acts as a college ambassador — answering
questions from prospective students, parents, and visitors about faculty,
departments, courses, labs, and notices. Runs entirely on one machine via
[Ollama](https://ollama.com) + Llama 3.1 8B Instruct, with no cloud API
dependency at inference time.

## Engineering Notebook

This project keeps its design history and technical reference as a set of
living documents in `docs/`, rather than one large file, so decisions stay
traceable as the project grows.

| Doc | Contents |
|---|---|
| [`docs/00_Project_Vision.md`](docs/00_Project_Vision.md) | Why this exists, goals, non-goals, personality, roadmap |
| [`docs/01_Architecture.md`](docs/01_Architecture.md) | System overview, hardware, high-level request flow |
| [`docs/02_Design_Decisions.md`](docs/02_Design_Decisions.md) | Model choice, RAG vs. no-RAG, platform choice — with rationale |
| [`docs/03_System_Prompts.md`](docs/03_System_Prompts.md) | Assistant identity, safety rules, tone |
| [`docs/04_Data_Schema.md`](docs/04_Data_Schema.md) | JSON schema for `faculty.json`, `courses.json`, `labs.json`, `notices.json` |
| [`docs/05_API.md`](docs/05_API.md) | HTTP endpoints (`/ask`, `/health`, `/refresh`) |
| [`docs/06_Backend.md`](docs/06_Backend.md) | Folder structure, module responsibilities, request lifecycle |
| [`docs/CHANGELOG.md`](docs/CHANGELOG.md) | Dated log of what was done |
| [`docs/TODO.md`](docs/TODO.md) | Known gaps and next steps |

## Project layout

```
rt/                      (project root)
├── README.md
├── requirements.txt
├── docs/                (this notebook)
├── app/
│   ├── main.py           # thin HTTP layer, no business logic
│   ├── schemas/          # AskRequest / AskResponse — the API boundary
│   ├── models/           # Faculty, Course, Notice, LabInfo — domain entities
│   ├── db/               # only layer allowed to read asset/*.json
│   ├── skill/            # live facts, search, prompt assembly, Ollama client
│   └── asset/            # dumb JSON storage + system prompt text
```

## Quick start

```powershell
ollama pull llama3.1:8b
uv sync
uv run uvicorn app.main:app --reload
```

See `docs/05_API.md` for endpoint details and `docs/06_Backend.md` for
setup/run instructions in full.
