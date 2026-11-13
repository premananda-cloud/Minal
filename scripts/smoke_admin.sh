#!/usr/bin/env bash
# P3.1 smoke test: the admin CLI with the REAL embedder and a REAL on-disk Chroma store.
# Uses throwaway stores under /tmp, so your real data is never touched.
#
#   bash scripts/smoke_admin.sh            # run, delete the temp stores at the end
#   bash scripts/smoke_admin.sh --keep     # keep them (e.g. to point ask.py at a store)
#
# The first run downloads the BGE embedding model, so it needs internet and can take a while.
# The embedder is kept on the CPU so it cannot collide with vLLM for GPU memory.
set -uo pipefail
cd "$(dirname "$0")/.."
export CUDA_VISIBLE_DEVICES=""

KEEP=0; [ "${1:-}" = "--keep" ] && KEEP=1
SAMPLE=samples/sample_department.json
[ -f "$SAMPLE" ] || { echo "missing $SAMPLE"; exit 2; }
if command -v minal-admin >/dev/null 2>&1; then ADMIN="minal-admin"; else ADMIN="uv run minal-admin"; fi
STORE1=/tmp/minal_smoke_store1; STORE2=/tmp/minal_smoke_store2; EXPORT=/tmp/minal_smoke_export.json
rm -rf "$STORE1" "$STORE2" "$STORE1.lock" "$STORE2.lock" "$EXPORT"

pass=0; fail=0
OUT=""; ERR=""; CODE=0
ERRF=$(mktemp)

ok()  { pass=$((pass+1)); echo "  PASS  $1"; }
bad() { fail=$((fail+1)); echo "  FAIL  $1"; [ -n "${2:-}" ] && echo "        $2"; }

# run <store> <label> <args...>   -> sets OUT ERR CODE (never aborts the script)
run() {
  local store=$1 label=$2; shift 2
  echo; echo "== $label"; echo "   \$ minal-admin $*"
  OUT=$(MINAL_DATA_DIR="$store" $ADMIN "$@" 2>"$ERRF"); CODE=$?
  ERR=$(cat "$ERRF")
  [ -n "$ERR" ] && echo "$ERR" | sed 's/^/   stderr: /' | head -8
  echo "   exit code: $CODE"
}
expect_code() { [ "$CODE" = "$1" ] && ok "$2 (exit $1)" || bad "$2" "expected exit $1, got $CODE"; }
# jq-free JSON check: py '<python expr on d>' ; prints the value, returns 0 if truthy
py() { python3 -I -c 'import sys,json; d=json.load(sys.stdin); r=('"$1"'); print(r); sys.exit(0 if r else 1)' <<<"$OUT" 2>&1; }
keys() { python3 -I -c 'import sys,json; d=json.load(sys.stdin); print(" ".join(sorted(i["record"].get("code") or i["record"].get("id") or "?" for i in d["result"]["items"])))' <<<"$OUT" 2>&1; }

run "$STORE1" "1. stats on an empty store" stats --json
expect_code 0 "stats runs on a new store"

run "$STORE1" "2. import dry run" import "$SAMPLE" --json
expect_code 0 "dry run succeeds"
v=$(py 'd["counts"]["create"]==16 and d["counts"]["error"]==0 and not d["applied"]') \
  && ok "dry run: 16 to create, 0 errors, nothing applied" || bad "dry-run counts" "$v | $OUT"

run "$STORE1" "3. import --apply (loads the real embedder)" import "$SAMPLE" --apply --json
expect_code 0 "apply succeeds"
v=$(py 'd["applied"] and d["counts"]["create"]==16') && ok "16 records created" || bad "apply counts" "$v | $OUT"

run "$STORE1" "4. import again (should be all unchanged)" import "$SAMPLE" --json
v=$(py 'd["counts"]["unchanged"]==16 and d["counts"]["create"]==0 and d["counts"]["update"]==0') \
  && ok "re-import is idempotent" || bad "re-import" "$v | $OUT"

run "$STORE1" "5. list courses as of 2026-11-13" list course --as-of 2026-11-13 --json
expect_code 0 "list works"
k=$(keys); [ "$k" = "CS101 CS102 CS201 CS301 EC101" ] \
  && ok "retired (CS999) and future (CS401) courses hidden today" || bad "as-of today" "got: $k"

run "$STORE1" "6. list courses as of 2027-02-01" list course --as-of 2027-02-01 --json
k=$(keys); [ "$k" = "CS101 CS102 CS201 CS301 CS401 EC101" ] \
  && ok "future course CS401 appears in 2027; CS999 still hidden" || bad "as-of 2027" "got: $k"

run "$STORE1" "7. show one course" show course CS201
expect_code 0 "show works"
echo "$OUT" | grep -q "Database Systems" && ok "shows the right record" || bad "show output" "$OUT"

run "$STORE1" "8. alignments for CS201" list alignment --filter course_code=CS201 --json
v=$(py 'd["result"]["total"]==1') && ok "one alignment for CS201" || bad "alignment filter" "$v"

run "$STORE1" "9. semantic search (real embeddings)" search "neural networks and model evaluation" --kind course --top-k 3 --json
expect_code 0 "search works"
top=$(python3 -I -c 'import sys,json
d=json.loads(sys.stdin.read())
def first_key(x):
    if isinstance(x,dict):
        if "key" in x: return x["key"]
        for v in x.values():
            r=first_key(v)
            if r: return r
    elif isinstance(x,list):
        for v in x:
            r=first_key(v)
            if r: return r
print(first_key(d["result"]))' <<<"$OUT" 2>&1)
[ "$top" = "CS301" ] && ok "top hit is CS301 (Machine Learning)" \
  || bad "search ranking" "top hit was '$top' (expected CS301); output shape may differ, check manually"

run "$STORE1" "10. retire a course that has an alignment (must be BLOCKED)" retire course CS201
expect_code 1 "retire is refused"
echo "$OUT $ERR" | grep -qi "in_use\|in use" && ok "error names the in-use reason" || bad "error text" "$ERR"

run "$STORE1" "11. retire with --cascade" retire course CS201 --cascade
expect_code 0 "cascade retire succeeds"
run "$STORE1" "12. CS201 and its alignment are gone from active lists" list course --as-of 2026-11-13 --json
k=$(keys); [ "$k" = "CS101 CS102 CS301 EC101" ] && ok "CS201 no longer listed" || bad "after retire" "got: $k"
run "$STORE1" "12b. alignments for CS201 after cascade" list alignment --filter course_code=CS201 --json
v=$(py 'd["result"]["total"]==0') && ok "its alignment was retired too" || bad "cascade of alignments" "$v"

run "$STORE1" "13. purge without --yes (must be refused as bad usage)" purge course CS301
expect_code 2 "purge needs --yes"

run "$STORE1" "14. export" export "$EXPORT"
expect_code 0 "export succeeds"
v=$(python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); print(len(d["faculty"]),len(d["courses"]),len(d["alignments"]))' "$EXPORT" 2>&1)
[ "$v" = "4 6 4" ] && ok "export has 4 faculty, 6 courses, 4 alignments (CS201 + its alignment excluded)" \
  || bad "export contents" "got: $v"

run "$STORE2" "15. restore: import the export into a brand new store" import "$EXPORT" --apply --json
expect_code 0 "restore succeeds"
v=$(py 'd["applied"] and d["counts"]["create"]==14 and d["counts"]["error"]==0') \
  && ok "export file re-imports cleanly (14 records)" || bad "restore" "$v | $OUT"

run "$STORE2" "16. persistence: a new process sees the restored data" list course --as-of 2026-11-13 --json
k=$(keys); [ "$k" = "CS101 CS102 CS301 EC101" ] && ok "data persisted across processes" || bad "persistence" "got: $k"

echo; echo "================ SUMMARY ================"
echo "passed: $pass   failed: $fail"
rm -f "$ERRF"
if [ "$KEEP" = 0 ]; then rm -rf "$STORE1" "$STORE2" "$STORE1.lock" "$STORE2.lock" "$EXPORT"; else echo "kept: $STORE1 $STORE2 $EXPORT"; fi
[ "$fail" = 0 ] && echo "P3.1 SMOKE TEST: PASS" || { echo "P3.1 SMOKE TEST: FAIL (see FAIL lines above)"; exit 1; }
