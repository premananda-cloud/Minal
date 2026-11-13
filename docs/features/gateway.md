# Feature: model gateway (P4b)

**Status:** Scripts written; tested against a fake vLLM; real-stack run pending

## 1. Purpose
One stable, authenticated endpoint in front of vLLM. The app calls LiteLLM with the model
name `minal-llm`, so swapping the model behind it changes nothing in the app.

## 2. Data flow
app -> LiteLLM (127.0.0.1:4000, master key) -> vLLM (127.0.0.1:8000, no key, localhost only)

## 3. Permissions
- Callers must send `Authorization: Bearer <LITELLM_MASTER_KEY>`.
- The key is generated on first run into `configs/litellm.local.env` (gitignored, mode 600).
- vLLM has no auth and listens on localhost only; nothing but the gateway should call it.

## 4. Connections
- LiteLLM runs in its own conda env, `minal-litellm` (`configs/litellm-env.yml`), so its
  pinned dependencies cannot clash with the app. The app only needs an OpenAI-compatible
  client pointed at the gateway.
- Model route: `hosted_vllm/minal-llm` at `http://127.0.0.1:8000/v1`
  (the name must match `SERVED_NAME` in `configs/vllm.env`).

## 5. Run
```bash
bash scripts/setup_litellm_env.sh   # once
bash scripts/serve_vllm.sh          # terminal 1
bash scripts/serve_litellm.sh       # terminal 2
bash scripts/check_litellm.sh       # terminal 3: the P4b gate
```

## 6. Behaviour notes
- Without a database, LiteLLM answers an unknown key with `400 No connected db` (it looks
  for a virtual key) and a missing key with `401`. Both mean rejected; the gate accepts either.
- Virtual keys (per-client keys, budgets) need Postgres. Deferred to P8.
- Startup crash `tzlocal() does not support non-zoneinfo timezones like Asia/Calcutta`
  happens when `TZ` names a zone the system lacks (legacy names live in `tzdata-legacy` on
  newer Debian/Ubuntu). `serve_litellm.sh` drops an unresolvable `TZ`.

## 7. Open questions
- Postgres for virtual keys, or keep one master key behind the API (P8).
