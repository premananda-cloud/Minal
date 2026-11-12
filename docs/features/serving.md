# Feature: model serving (P4a)

**Status:** Decided; scripts written, awaiting first run on the GPU machine

## 1. Purpose
Run a local instruct model on the 12 GB GPU, reachable over an OpenAI-compatible
endpoint. The app never calls it directly; LiteLLM (P4b) sits in front.

## 2. Decision
**`Qwen/Qwen2.5-7B-Instruct-AWQ`, served by vLLM with `awq_marlin`.**
Fallback: GPTQ-Int4 variant, only if the AWQ Marlin kernel is unstable on this
card or driver. Reported throughput difference between them is about 1%, so it is
a stability fallback, not a memory saving.

## 3. Starting configuration
```bash
vllm serve Qwen/Qwen2.5-7B-Instruct-AWQ \
  --quantization awq_marlin \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.80 \
  --enforce-eager
```

| Setting | Value | Reason |
| :--- | :--- | :--- |
| `--max-model-len` | 4096 | Always pass it explicitly; the model default is far larger and is a common cause of OOM on 12-16 GB cards |
| `--gpu-memory-utilization` | 0.80 | Leaves room for the embedder and OS |
| `--enforce-eager` | on | Skips CUDA graph memory during bring-up; revisit once VRAM is stable |

Tuning: if 4096 is stable with headroom, try 6144.

## 4. Things to know
- vLLM pre-allocates KV cache up to `gpu-memory-utilization`, so `nvidia-smi` will
  look full regardless of quantization. 4-bit weights (about 5.3 GiB) buy KV-cache
  capacity and context length, not a lower usage number.
- The BGE embedder runs in the app process. If it uses the GPU it shares the VRAM
  left over by vLLM. Measure with both loaded, not vLLM alone.
- vLLM lives in its own environment (conflicts with Docling/torch). Launch script in
  `scripts/`, config in `configs/`.

## 5. How to run
```bash
bash scripts/setup_vllm_env.sh   # once: creates .venv-vllm, installs vLLM
bash scripts/serve_vllm.sh       # terminal 1; settings live in configs/vllm.env
bash scripts/check_vllm.sh       # terminal 2: curl test + peak VRAM
```
The served model name is `minal-llm`, so LiteLLM (P4b) and the app never depend on
which model sits behind it.

## 6. Test gate
`curl` to vLLM `/v1/chat/completions` returns text, then record in `STATUS.md`:

```
P4a evidence:
- Model / quantization:
- max_model_len, gpu_memory_utilization, enforce_eager:
- curl returned text on first attempt (yes/no):
- nvidia-smi peak during inference (GB), with the embedder loaded:
- Headroom (12 - peak):
- OOM observed (none / at which setting):
```
The measured peak decides whether 6144 is safe or 4096 stays.

## 7. Open questions
- Embedding model for production (currently BGE). Benchmark Qwen3-Embedding-0.6B
  against BGE-M3 on the P7b eval set before changing it (P9a). Quality claims for
  both are from third-party benchmarks and are not yet verified on our data.
