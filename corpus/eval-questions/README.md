# eval-questions/ — HELD-OUT EVAL SOURCE — **NEVER INDEX THESE**

Real student chat-questions asked live during sessions (corpus-**independent**: students asked them, they
were not authored from the notes). This is the leak-safe held-out evaluation source (AGENTS.md §2 gate 4,
`docs/genacademy-rag-foundation.md`).

**Hard rule:** files in this folder are NEVER ingested into the retrieval index, NEVER placed in prompts,
few-shots, or the demo script. The ingestion code indexes `notes/ transcripts/ slides/ handouts/` only.

Filename rule before splitting: normalize to lowercase kebab-case and keep exactly one file per
week/session source. Case variants or duplicate exports can double-count questions and break stable IDs
across macOS/Linux.

NotebookLM exports, generated quizzes, and deep-note "Quiz Yourself" items are corpus-derived seed/dev
material, not held-out eval. Keep them out of this folder; add a separate ignored drop-zone only when
that material is actually introduced.
