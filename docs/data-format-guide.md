# Data Format Guide — `app/asset/*.json`

This is a reference for anyone adding or editing the JSON files the chatbot
reads from `app/asset/`. Each file is loaded straight into a Pydantic model
in `app/models/entities.py`. **Field names in the JSON must match the model
field names exactly** — a renamed or missing required field will either
crash the whole app on startup, or (worse) silently get dropped with no
error at all. Both failure modes have happened before; this doc exists so
they don't happen again.

## How loading works, and why field names matter

`app/db/repository.py` reads each file and constructs model objects like
`Faculty(**record)`. Pydantic matches JSON keys to model fields **by exact
name**. There are two ways this goes wrong:

1. **Missing required field** — the whole `refresh()` call raises a
   `ValidationError` and the server 500s on every request, not just the
   file that's wrong. (`code`/`title` on `Course`, `body` on `Notice` are
   required — see history in `CHANGELOG.md`.)
2. **Silent data loss** — if the mismatched field is *optional* in the
   model (e.g. `specialization`, `room`), Pydantic doesn't error. It just
   sets that field to `null` and drops your data with no warning. This is
   the more dangerous case because nothing tells you it happened.

Extra keys not in the model (e.g. `fees`, `intake`, `id`) are harmless —
Pydantic ignores unknown fields by default. Feel free to keep extra
metadata in a record for your own reference; the app just won't use it
unless a developer adds it to the model.

**Rule of thumb:** when adding a field, check `app/models/entities.py`
first and use the exact name written there.

---

## `faculty.json` → `Faculty`

| JSON key         | Required? | Type              | Notes                                  |
|-------------------|-----------|-------------------|-----------------------------------------|
| `name`            | **Yes**   | string            |                                          |
| `designation`     | **Yes**   | string            | e.g. "Assistant Professor"              |
| `department`      | **Yes**   | string            |                                          |
| `email`           | No        | string            |                                          |
| `room`            | No        | string            | **not** `office`                        |
| `specialization`  | No        | list of strings   | **not** `expertise`                     |

```json
{
  "name": "Dr. A. Singh",
  "designation": "Professor & Head",
  "department": "Computer Science and Engineering",
  "email": "a.singh@nielit.gov.in",
  "room": "CSE Block, Room 101",
  "specialization": ["Artificial Intelligence", "Machine Learning", "Data Science"]
}
```

## `courses.json` → `Course`

| JSON key       | Required? | Type   | Notes                     |
|-----------------|-----------|--------|----------------------------|
| `code`          | **Yes**   | string | **not** `id`               |
| `title`         | **Yes**   | string | **not** `name`             |
| `department`    | **Yes**   | string |                             |
| `duration`      | No        | string |                             |
| `eligibility`   | No        | string |                             |
| `description`   | No        | string |                             |

```json
{
  "code": "BTECH-CSE",
  "title": "B.Tech in Computer Science Engineering",
  "department": "Computer Science",
  "duration": "4 years (8 semesters)",
  "eligibility": "10+2 with PCM, valid JEE Main score",
  "description": "A comprehensive undergraduate programme covering..."
}
```

## `notices.json` → `Notice`

| JSON key      | Required? | Type              | Notes                                          |
|----------------|-----------|-------------------|-------------------------------------------------|
| `title`        | **Yes**   | string            |                                                  |
| `date`         | **Yes**   | string (ISO date) | `YYYY-MM-DD`                                    |
| `body`         | **Yes**   | string            | **not** `content`                               |
| `expires_on`   | No        | string (ISO date) | `YYYY-MM-DD`; omit or `null` = never expires    |

```json
{
  "title": "Guest Lecture on AI in Healthcare",
  "date": "2026-07-20",
  "body": "We are hosting Dr. S. Kumar for a guest lecture on 28 July 2026...",
  "expires_on": "2026-07-29"
}
```

`get_notices(active_only=True)` filters out any notice whose `expires_on`
is in the past. If you want a notice to stay up indefinitely, leave
`expires_on` out entirely — don't set it to an empty string.

## `labs.json` → `LabInfo`

| JSON key      | Required? | Type            | Notes |
|----------------|-----------|-----------------|-------|
| `name`         | **Yes**   | string          |       |
| `department`   | **Yes**   | string          |       |
| `description`  | No        | string          |       |
| `equipment`    | No        | list of strings |       |

```json
{
  "name": "AI & ML Lab",
  "department": "Computer Science",
  "description": "GPU-equipped lab for AI/ML training and research.",
  "equipment": ["RTX 4070 workstation", "Networked storage"]
}
```

---

## Before you commit a change: validate locally

Don't wait for the server to tell you a file is broken — check it
yourself first. Save this as a throwaway script (or run it in a Python
shell from the project root) and point it at whichever file you edited:

```python
import json
from app.models.entities import Faculty, Course, Notice, LabInfo

FILES = {
    "app/asset/faculty.json": Faculty,
    "app/asset/courses.json": Course,
    "app/asset/notices.json": Notice,
    "app/asset/labs.json": LabInfo,
}

for path, model in FILES.items():
    with open(path, encoding="utf-8") as f:
        records = json.load(f)
    for i, record in enumerate(records):
        model(**record)  # raises ValidationError with the exact field/reason if wrong
    print(f"OK  {path}  ({len(records)} records)")
```

If a record is invalid, this fails loudly with the exact field and reason
— the same way it would in production, just before you've broken anything
live.

## Checklist for adding a new entry

1. Open `app/models/entities.py` and find the model for the file you're editing.
2. Copy an existing record in the JSON file as your template — don't type keys from memory.
3. Fill in every **required** field. Optional fields can be omitted entirely (don't set them to `""` or `null` explicitly — just leave the key out).
4. Run the validation script above before committing.
5. Restart the server (or call whatever triggers `db.refresh()`) so the in-memory cache picks up the change — edits to the JSON files are not read live.
