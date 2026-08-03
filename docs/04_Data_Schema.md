# Data Schema

Describes the structure of the JSON files under `app/asset/`. Each file is
a UTF-8-encoded JSON array of objects with the fields defined below.
Fields are case-sensitive and must match exactly; parsers should ignore
any unknown/extra fields rather than failing.

---

## `courses.json`

Academic courses offered.

| Field | Type | Description | Example | Required |
|---|---|---|---|---|
| `code` | `string` | Unique course code (acronym) | `"CCC"` | Yes |
| `title` | `string` | Full title of the course | `"Course on Computer Concepts"` | Yes |
| `department` | `string` | Department offering the course | `"General"` | Yes |
| `duration` | `string` | Duration (hours, weeks, etc.) | `"80 hours"` | Yes |
| `eligibility` | `string` | Minimum educational qualification required | `"8th pass"` | Yes |
| `description` | `string` | Brief description of the course content | `"Basic computer literacy..."` | Yes |

```json
{
  "code": "CCC",
  "title": "Course on Computer Concepts",
  "department": "General",
  "duration": "80 hours",
  "eligibility": "8th pass",
  "description": "Basic computer literacy course for beginners."
}
```

---

## `faculty.json`

Faculty and staff members.

| Field | Type | Description | Example | Required |
|---|---|---|---|---|
| `name` | `string` | Full name | `"Dr. Sanasam"` | Yes |
| `designation` | `string` | Job title / designation | `"Scientist-C / HoD"` | Yes |
| `department` | `string` | Department they belong to | `"Computer Science"` | Yes |
| `email` | `string` | Official email address | `"example.singh@nielit.gov.in"` | Yes |
| `room` | `string` | Office room number/identifier | `"CS-101"` | Yes |
| `specialization` | `array<string>` | Areas of expertise | `["Machine Learning", "Networking"]` | Yes |

```json
{
  "name": "Dr. Sanasam",
  "designation": "Scientist-C / HoD",
  "department": "Computer Science",
  "email": "example.singh@nielit.gov.in",
  "room": "CS-101",
  "specialization": ["Machine Learning", "Networking"]
}
```

---

## `labs.json`

Laboratory facilities.

| Field | Type | Description | Example | Required |
|---|---|---|---|---|
| `name` | `string` | Name of the lab | `"AI & ML Lab"` | Yes |
| `department` | `string` | Department that owns/manages the lab | `"Computer Science"` | Yes |
| `description` | `string` | Brief description of the lab's purpose | `"GPU-equipped lab for AI/ML..."` | Yes |
| `equipment` | `array<string>` | Major equipment/resources available | `["RTX 4070 workstation", "Networked storage"]` | Yes |

```json
{
  "name": "AI & ML Lab",
  "department": "Computer Science",
  "description": "GPU-equipped lab for AI/ML training and research.",
  "equipment": ["RTX 4070 workstation", "Networked storage"]
}
```

---

## `notices.json`

Announcements and notices with expiry dates. The app filters this to
active-only (not expired) notices by default before injecting into the
prompt.

| Field | Type | Description | Example | Required |
|---|---|---|---|---|
| `title` | `string` | Headline of the notice | `"Admission Open"` | Yes |
| `date` | `string` | Publication date (`YYYY-MM-DD`) | `"2026-07-01"` | Yes |
| `body` | `string` | Full content of the notice | `"Admissions for the next CCC..."` | Yes |
| `expires_on` | `string` | Expiration date (`YYYY-MM-DD`) | `"2026-08-31"` | Yes |

```json
{
  "title": "Admission Open",
  "date": "2026-07-01",
  "body": "Admissions for the next CCC batch are open. Visit the admin office for details.",
  "expires_on": "2026-08-31"
}
```

---

## General notes

- All files are UTF-8-encoded JSON.
- Fields are case-sensitive and must exactly match the names above.
- Array fields (`specialization`, `equipment`) may contain zero or more strings.
- Dates use ISO 8601 (`YYYY-MM-DD`) throughout.
- Keep each file to roughly ≤100 entries for latency (see `02_Design_Decisions.md`, D2/D5, for when to revisit this).
- `db/repository.py` is the only module allowed to read these files directly (see `06_Backend.md`).
