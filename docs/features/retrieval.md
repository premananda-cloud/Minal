# Feature: retrieval (AI access to college data)

**Status:** Draft

## 1. Purpose
Given a question, return the college records the LLM should read, as numbered
passages plus a prompt-ready context string, within a size budget.

## 2. Data flow
question -> exact course-code lookup (+ who teaches it) -> semantic search ->
dedupe -> context budget -> RetrievalResult
Exact matches come first because embeddings can miss precise facts (credits,
instructors). Semantic hits fill in the rest.

## 3. Permissions
Receives a `DatabaseReader` only. It has no write methods, so retrieval cannot
modify data. Only active records are searched; history is never shown to the AI.

## 4. Connections
- `minal.db.DatabaseReader` (get, list_records, search).
- Optional LangChain adapter (`langchain_adapter.py`) for chains.
- Does not talk to LiteLLM/vLLM; prompt composition belongs to `llm/`.

## 5. Failure and audit
- Unknown course codes are ignored; the question falls through to semantic search.
- Embedding-model mismatch raises (a config problem, not a "no results").
- Date handling: `as_of` defaults to today, so records valid in the future or
  expired are hidden unless a date is given.

## 6. Open questions
- Faculty lookup by name/id (exact), not just course codes?
- Score threshold: tune `min_score` against real questions once data exists.
- Query rewriting for follow-up questions ("and who teaches it?") belongs in llm/.
