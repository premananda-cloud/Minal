# Project Vision

**Version:** 0.1
**Last updated:** 24 July 2026
**Status:** Planning & Architecture

---

## 1. Vision

Develop a local, AI-powered college ambassador capable of answering questions
from prospective students, parents, and visitors — instantly, naturally, and
without an internet connection.

The assistant should be able to speak to:

- College facilities
- Faculty
- Departments
- Courses
- Events
- Admissions
- Laboratories
- Campus services

Intended deployment surfaces (over time): information kiosk, reception desk,
public website, and eventually mobile/web apps — all backed by the same local
server.

## 2. Goals

- Natural conversation, not a search-engine feel
- Very low latency
- Accurate information, grounded in real data
- Easy for non-technical college staff to update
- Fully offline — no dependence on cloud APIs

## 3. Non-goals (Phase 1)

Deliberately out of scope for the first phase:

- Voice input/output
- Multi-language support
- Student login
- Attendance tracking
- ERP integration
- Admission processing
- Live internet search

## 4. User Experience

A visitor should feel they're speaking with a knowledgeable college
representative, not querying a database. Example questions the assistant
should handle conversationally:

- "How many faculty members are there?"
- "Tell me about the AI Lab."
- "Which department offers Data Science?"
- "What short-term courses are available?"
- "Who teaches Operating Systems?"
- "Where is the Mechanical Workshop?"

Responses should be concise, polite, and conversational — see
`03_System_Prompts.md` for the tone rules that enforce this.

## 5. Personality

The assistant represents the institution, so its tone is:

- Professional
- Friendly
- Patient
- Helpful
- Concise

It avoids sarcasm, political opinions, personal advice, and speculation.

## 6. Phase Roadmap

| Phase | Focus | Status |
|---|---|---|
| 1 | Architecture — model selection, prompt design, dataset format, local inference | Complete |
| 2 | Knowledge base — faculty, departments, courses, infrastructure data | Not started |
| 3 | Backend — API, prompt assembly, dynamic context, logging | Not started |
| 4 | Frontend — chat UI, reception interface, kiosk mode | Not started |
| 5 | Administration — staff editor, dataset management, update interface | Not started |
| 6 | Advanced features — voice, multiple languages, vision, campus map, tool calling, database integration | Planned |

### Current status snapshot

| Component | Status |
|---|---|
| Vision | Complete |
| Architecture | Complete |
| Model selection | Complete |
| Data strategy | Complete |
| Guardrails | Complete |
| Backend | Not started |
| Frontend | Not started |
| Dataset | Not started |
| Voice | Planned |
| Deployment | Planned |

## 7. Future Research

Ideas parked for later phases, not yet committed to:

- Function/tool calling
- Room navigation
- Voice synthesis and speech recognition
- Student document lookup
- Timetable lookup
- Event scheduling
- QR code support
- Campus map search
- Multi-agent architecture
