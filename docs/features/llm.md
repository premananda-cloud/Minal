# Feature: llm (client and fake), P5a

**Status:** Built; unit tests pass; integration test pending on the real stack

## 1. Purpose
Let the answer chain call the language model through one typed interface, and let tests
run the chain with no model or network.

## 2. Data flow
answer chain -> `LLM.complete(CompletionRequest)` -> `LiteLLMClient` -> LiteLLM
(`/v1/chat/completions`, model `minal-llm`) -> vLLM -> `CompletionResult`.
Nothing is written anywhere; the client is stateless apart from its HTTP connection.

## 3. Permissions
- The client holds the gateway key (`SecretStr`, never printed). It has no access to the database.
- Config from `LLMConfig` or the environment: `MINAL_LLM_BASE_URL`, `MINAL_LLM_MODEL`,
  `MINAL_LLM_API_KEY` (falls back to `LITELLM_MASTER_KEY`), `MINAL_LLM_TIMEOUT_S`.

## 4. Connections
- Talks only to the LiteLLM gateway (default `http://127.0.0.1:4000/v1`), never to vLLM.
- Uses httpx, already a dependency. No new dependency, no SDK, no `litellm` import in the app.
- `FakeLLM` ships in the package (`minal.llm.FakeLLM`) so every test directory can import it.

## 5. Failure and audit
Every failure becomes a stable error with a `code`:

| Code | When |
| :--- | :--- |
| `llm_unavailable` | connection refused, HTTP 429 or 5xx |
| `llm_timeout` | no answer within `timeout_s` |
| `llm_auth_failed` | HTTP 401/403, or the gateway's `no_db_connection` 400 for an unknown key |
| `llm_bad_request` | other 4xx (unknown model, prompt too long); message kept in `details` |
| `llm_bad_response` | body not in chat-completions shape, or no text content |

An empty completion string is returned as-is (not an error); the chain decides what to do.
No retries yet. Request/response logging and tracing arrive in P7a.

## 6. Defaults worth knowing
- `temperature` defaults to 0.2 (vLLM's own default is 0.7), `max_tokens` to 512.
- `FakeLLM` records every request (`calls`, `last`, `last_prompt_text()`) so P5b tests can
  assert the prompt contains only retrieved text.

## 7. Open questions
- Retry and backoff for `llm_unavailable` / `llm_timeout` (P6, when the API needs it).
- Streaming responses (not needed until a chat UI exists).
