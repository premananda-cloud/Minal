# Feature: admin CLI

**Status:** Built, untested

## 1. Purpose
Local tool for admins to add, change, retire, inspect, import and export college data.
Contains no database logic: every action is a `Dispatcher` command.

## 2. Data flow
CLI args -> Dispatcher -> Database (writer) -> embedder -> Chroma
Import: JSON file -> validate everything (dry run) -> write only if the whole file is clean.
Export: Chroma -> JSON file (current records only; history is not exported).

## 3. Permissions
- Local only. There is no network surface; run it on the machine that holds the store.
- Holds the full `Database` (reader + writer). The public API never gets this.
- A lock file (`<data-dir>.lock`) stops two processes opening the embedded store at once.

## 4. Safety rules (enforced in the db layer, not just the CLI)
- `retire` is blocked while alignments valid today still use the course/faculty record.
  Past or future-dated alignments do not block it.
- `purge` is blocked by any active alignment, current or past.
- `--cascade` also removes those alignments; `--force` proceeds and leaves them dangling.
- `purge` additionally needs `--yes`. `edit` cannot change key fields (code, id, term).
- Prefer setting `valid_to` on a record that has ended (a departed faculty member,
  a discontinued course) over retiring it: history and "as of" answers stay correct.

## 5. Import / export format
One JSON file: `{"version": 1, "faculty": [...], "courses": [...], "alignments": [...]}`.
Loaded in that order so references resolve. Any validation error blocks the apply and
nothing is written. `export` output can be fed straight back to `import`.

## 6. Known limits (deliberate, for now)
- JSON only; no CSV.
- Import never deletes: records absent from the file are left alone.
- Cascade is not atomic: if it fails midway, some alignments may already be retired.
- Export omits history.
- Alignment = faculty teaching a course in a term. Program / outcome mapping is a later patch.
