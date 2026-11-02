# Feature: db (college data store)

**Status:** Draft

## 1. Purpose
Hold college data (courses, faculty, course-faculty alignments) in ChromaDB so the
AI can search it, and give admins safe ways to add, change, retire and inspect it.

## 2. Data flow
admin CLI -> Dispatcher -> Database (writer) -> embedder -> Chroma
retrieval -> DatabaseReader -> embedder (query) -> Chroma -> StoredRecord/Hit

Each record is rendered to text (`to_text`), embedded, and stored with filterable
metadata plus the full record as JSON. Updating a record archives the old version
(`<key>#v<N>`); search and list see only `active` records unless asked.

## 3. Permissions
- `DatabaseReader`: get, list, search, history, stats. Given to retrieval.
- `DatabaseWriter`: put, retire, purge, reindex. Given to admin only.
- Enforcement is by object: a reader has no write methods, and a Dispatcher built
  on a reader exposes no write commands.

## 4. Connections
- Embedded Chroma (PersistentClient). One owning process at a time; share via `db.as_reader()`.
- Embedding model recorded per collection; mismatched model is refused until `reindex`.

## 5. Failure and audit
- Embedding runs before any write, so a failed embed never changes stored data.
- Errors are stable codes: invalid_request, not_found, reference_missing,
  embedding_model_mismatch, unknown_command, internal_error.
- Version history is the audit trail of what changed and when.

## 6. Open questions
- Does "alignment" also need course-to-program-outcome mapping?
- Visibility tags per record (role-based filtering)?
- Block retire/purge of a course or faculty that still has active alignments?
