# JSON File Format Documentation

This document describes the structure and schema of the JSON data files used by the system. Each file contains an array of objects with defined fields. All files are UTF-8 encoded JSON.

---

## 1. `courses.json`

Contains information about academic courses offered.

| Field         | Type     | Description                                 | Example                     | Required |
|---------------|----------|---------------------------------------------|-----------------------------|----------|
| `code`        | `string` | Unique course code (acronym).               | `"CCC"`                     | Yes      |
| `title`       | `string` | Full title of the course.                   | `"Course on Computer Concepts"` | Yes   |
| `department`  | `string` | Department offering the course.             | `"General"`                 | Yes      |
| `duration`    | `string` | Duration (e.g., hours, weeks).              | `"80 hours"`                | Yes      |
| `eligibility` | `string` | Minimum educational qualification required. | `"8th pass"`                | Yes      |
| `description` | `string` | Brief description of the course content.    | `"Basic computer literacy..."` | Yes   |

**Example:**
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

## 2. `faculty.json`

Contains information about faculty/staff members.

| Field            | Type          | Description                                      | Example                       | Required |
|------------------|---------------|--------------------------------------------------|-------------------------------|----------|
| `name`           | `string`      | Full name of the faculty member.                 | `"Dr. Sanasam"`               | Yes      |
| `designation`    | `string`      | Job title or designation.                        | `"Scientist-C / HoD"`         | Yes      |
| `department`     | `string`      | Department they belong to.                       | `"Computer Science"`          | Yes      |
| `email`          | `string`      | Official email address (format: `name@domain`).  | `"example.singh@nielit.gov.in"` | Yes   |
| `room`           | `string`      | Office room number or identifier.                | `"CS-101"`                    | Yes      |
| `specialization` | `array` of `string` | List of areas of expertise/specialization.   | `["Machine Learning", "Networking"]` | Yes |

**Example:**
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

## 3. `labs.json`

Contains details about laboratory facilities.

| Field         | Type          | Description                                      | Example                              | Required |
|---------------|---------------|--------------------------------------------------|--------------------------------------|----------|
| `name`        | `string`      | Name of the lab.                                 | `"AI & ML Lab"`                      | Yes      |
| `department`  | `string`      | Department that owns/manages the lab.            | `"Computer Science"`                 | Yes      |
| `description` | `string`      | Brief description of the lab's purpose.          | `"GPU-equipped lab for AI/ML..."`    | Yes      |
| `equipment`   | `array` of `string` | List of major equipment or resources available. | `["RTX 4070 workstation", "Networked storage"]` | Yes |

**Example:**
```json
{
  "name": "AI & ML Lab",
  "department": "Computer Science",
  "description": "GPU-equipped lab for AI/ML training and research.",
  "equipment": ["RTX 4070 workstation", "Networked storage"]
}
```

---

## 4. `notices.json`

Contains announcements and notices with expiry dates.

| Field         | Type     | Description                                      | Example                              | Required |
|---------------|----------|--------------------------------------------------|--------------------------------------|----------|
| `title`       | `string` | Headline of the notice.                          | `"Admission Open"`                   | Yes      |
| `date`        | `string` | Publication date (ISO 8601 format: `YYYY-MM-DD`).| `"2026-07-01"`                      | Yes      |
| `body`        | `string` | Full content of the notice.                      | `"Admissions for the next CCC..."`   | Yes      |
| `expires_on`  | `string` | Expiration date (ISO 8601 format: `YYYY-MM-DD`). | `"2026-08-31"`                      | Yes      |

**Example:**
```json
{
  "title": "Admission Open",
  "date": "2026-07-01",
  "body": "Admissions for the next CCC batch are open. Visit the admin office for details.",
  "expires_on": "2026-08-31"
}
```

---

## General Notes

- All files are UTF‑8 encoded JSON.
- Fields are case‑sensitive and must exactly match the names shown.
- Arrays (e.g., `specialization`, `equipment`) may contain zero or more strings.
- Dates (in `notices.json`) are expected in `YYYY-MM-DD` format.
- No additional fields beyond those listed are expected; parsers should ignore unknown fields if possible.
