Yes. Based on your notes, I would actually treat this as an **Engineering Record / Design Decision Document (DDD)** instead of scattered notes. That way every phase has a reason behind it, making it easier to continue development months later or even hand the project to someone else.

---

# Minal AI Assistant

## Engineering Record

**Version:** 0.1 (Phase 1)
**Date:** 24 July 2026
**Project Status:** Planning & Architecture

---

# 1. Project Overview

## Vision

Develop a local AI-powered college ambassador capable of answering questions from prospective students, parents, and visitors.

The assistant should provide instant, natural conversation regarding:

* College facilities
* Faculty
* Departments
* Courses
* Events
* Admissions
* Laboratories
* Campus services

The system should eventually run:

* Information kiosk
* Reception desk
* Website
* Local server
* Future mobile/web applications

---

# Goals

Primary goals:

* Natural conversation
* Very low latency
* Accurate information
* Easy to update
* Works offline
* No dependence on cloud APIs
* Simple enough for college staff to maintain

---

# Non-goals

Phase 1 intentionally excludes:

* Voice input/output
* Multi-language support
* Student login
* Attendance
* ERP integration
* Admission processing
* Internet search

---

# 2. User Experience

The visitor should feel they are speaking with a knowledgeable college representative rather than a search engine.

Example questions:

> How many faculty members are there?

> Tell me about the AI Lab.

> Which department offers Data Science?

> What short-term courses are available?

> Who teaches Operating Systems?

> Where is the Mechanical Workshop?

Responses should be concise, polite, and conversational.

---

# 3. Overall Architecture

```
Visitor
     │
     ▼

Chat Interface
     │
     ▼

Backend Server
     │
     ├── System Prompt
     ├── Current Time
     ├── College Dataset
     ├── Tools (Future)
     │
     ▼

Ollama

     │
     ▼

Llama 3.1 8B Instruct
```

---

# 4. Model Decision

## Selected Model

Llama 3.1 8B Instruct

Running locally through Ollama.

---

## Reasons

### Fast response

Public interaction should feel instantaneous.

Large delays make the assistant appear unintelligent.

---

### GPU compatibility

Target hardware:

RTX 4070 Super

12 GB VRAM

The 8B quantized model occupies roughly half of available VRAM, leaving sufficient space for:

* Context window
* KV cache
* Operating system
* Future tool usage

---

### Instruction following

The model follows conversational instructions reliably while resisting prompt injection better than older models.

---

# Decision

Approved.

---

# 5. Knowledge Architecture

## Decision

Do **not** use Retrieval-Augmented Generation (RAG) initially.

Instead:

Inject the complete college dataset into the prompt.

---

## Reasoning

Estimated knowledge:

* Faculty
* Departments
* Labs
* Courses

Approximately:

100 faculty

15,000 words

Well below Llama's context limit.

Advantages:

* Zero retrieval latency
* Simpler implementation
* No vector database
* No embedding pipeline
* Easier debugging

---

## Future Upgrade Trigger

Move to RAG only when:

* Knowledge exceeds context window
* Multiple colleges are supported
* Documents become very large
* PDFs become searchable

---

# Decision

Approved.

---

# 6. Data Pipeline

Current flow:

```
Faculty Forms

↓

Structured JSON

↓

Backend

↓

Prompt Builder

↓

LLM
```

Future:

```
Faculty Portal

↓

Validation

↓

Database

↓

Prompt Builder

↓

Assistant
```

---

# 7. Dynamic Context

The backend injects runtime information.

Examples:

Current date

Current time

Upcoming events

Office hours

Holiday notices

Admission status

This prevents hallucination regarding temporal questions.

---

# 8. Safety Rules

The assistant must:

* Never invent faculty
* Never invent departments
* Never fabricate phone numbers
* Never guess office locations
* Never provide unofficial admission information

If information is unavailable:

> "I don't have that information. Please contact the reception office."

---

# 9. Personality

The assistant represents the institution.

Tone:

* Professional
* Friendly
* Patient
* Helpful
* Concise

Avoid:

* Sarcasm
* Political opinions
* Personal advice
* Speculation

---

# 10. Platform Decisions

Development Platform:

Windows

Reason:

* Ollama runs locally
* Direct GPU access
* Easier debugging
* Lower networking complexity
* Faster development cycle

WSL may be used later for Docker or deployment testing.

---

# 11. Phase Roadmap

## Phase 1

Architecture

* Model selection
* Prompt design
* Dataset format
* Local inference

Status: Completed

---

## Phase 2

Knowledge Base

* Faculty
* Departments
* Courses
* Infrastructure

---

## Phase 3

Backend

* API
* Prompt assembly
* Dynamic context
* Logging

---

## Phase 4

Frontend

* Chat UI
* Reception interface
* Kiosk mode

---

## Phase 5

Administration

* Staff editor
* Dataset management
* Update interface

---

## Phase 6

Advanced Features

* Voice interaction
* Multiple languages
* Vision
* Campus map
* Tool calling
* Database integration

---

# 12. Future Research

Potential additions:

* Function calling
* Room navigation
* Voice synthesis
* Speech recognition
* Student document lookup
* Timetable lookup
* Event scheduling
* QR code support
* Campus map search
* Multi-agent architecture

---

# Current Status

| Component       | Status      |
| --------------- | ----------- |
| Vision          | Complete    |
| Architecture    | Complete    |
| Model Selection | Complete    |
| Data Strategy   | Complete    |
| Guardrails      | Complete    |
| Backend         | Not Started |
| Frontend        | Not Started |
| Dataset         | Not Started |
| Voice           | Planned     |
| Deployment      | Planned     |

---

I would also recommend organizing this as an **Engineering Notebook** rather than a single document. For example:

```
Minal-AI/
│
├── docs/
│   ├── 00_Project_Vision.md
│   ├── 01_Architecture.md
│   ├── 02_Design_Decisions.md
│   ├── 03_System_Prompts.md
│   ├── 04_Data_Schema.md
│   ├── 05_API.md
│   ├── 06_Backend.md
│   ├── 07_Frontend.md
│   ├── 08_Deployment.md
│   ├── CHANGELOG.md
│   └── TODO.md
│
├── backend/
├── frontend/
├── data/
├── prompts/
└── README.md
```

This structure scales much better as the project grows and gives you a proper engineering record from the very beginning.
