# eval-questions/ — HELD-OUT EVAL SOURCE — **NEVER INDEX THESE**

Real student chat-questions asked live during sessions (corpus-**independent**: students asked them, they
were not authored from the notes). This is the leak-safe held-out evaluation source (AGENTS.md §2 gate 4,
`docs/genacademy-rag-foundation.md`).

**Hard rule:** files in this folder are NEVER ingested into the retrieval index, NEVER placed in prompts,
few-shots, or the demo script. The ingestion code indexes `notes/ transcripts/ slides/ handouts/` only.
NotebookLM-exported quizzes/flashcards (AI-generated, course-derived) also live here as dev/seed material
— spot-check before trusting any as gold.
