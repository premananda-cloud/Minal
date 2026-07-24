## Phase 1 Architecture Report: Minal AI Assistant Secretary

**Date:** July 24, 2026
**Primary Objective:** Develop a fast, interactive, and reliable college ambassador AI to answer visitor queries, capable of running locally on a 12 GB VRAM GPU.

### 1. Model Selection

**Decision:** Llama 3.1 8B Instruct (via Ollama)
**Reasoning:**

* **VRAM Efficiency & Headroom:** At quantized levels (like Q4_K_M), the 8B model occupies only ~5.5 GB of VRAM. This leaves over 6 GB of available memory on a 12 GB GPU for the context window (KV Cache) and system overhead, ensuring the model never pages to slower system RAM during heavy use.
* **Speed as UX:** The 8B parameter size generates tokens almost instantly on local hardware. For a live, public-facing interface, ultra-low latency is critical to making the interaction feel conversational and responsive.
* **Alignment & Tone:** The 3.1 Instruct version possesses excellent post-training alignment. It handles emotional nuances effectively (e.g., guiding confused or stressed visitors) while remaining stubborn against casual trick questions or attempts to break its rules.

### 2. Data Pipeline Architecture

**Decision:** Direct Context Injection (Full Dataset) instead of Retrieval-Augmented Generation (RAG).
**Reasoning:**

* **Scale-Appropriate Engineering:** The total dataset is small — approximately 100 faculty members plus course details, translating to roughly 15,000 words.
* **Context Window Utilization:** Llama 3.1 8B features a 128,000-token context window. The entire college dataset comfortably fits directly into the model's short-term memory, consuming less than 10% of its capacity.
* **Zero-Latency Retrieval:** Bypassing a vector database (like ChromaDB or FAISS) eliminates the search-step latency and the risk of the search algorithm failing to fetch the right document. The model effectively "memorizes" the roster for every interaction.

### 3. Guardrails and Dynamic Context

**Decision:** Pre-computation of dynamic variables combined with strict boundary prompting.
**Reasoning:**

* **Time Awareness:** LLMs lack an internal clock. The backend must dynamically inject the exact date and time at the start of every session so the model can accurately resolve temporal queries (e.g., "Is the lab open tomorrow?").
* **Hallucination Prevention:** A strict directive will be written into the system prompt, instructing the model to playfully reject queries about non-existent staff or subjects rather than attempting to fabricate plausible answers to satisfy the user.
