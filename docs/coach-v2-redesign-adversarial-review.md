# GenAcademy Coach V2 — Pre-Build Adversarial Review

> **Context.** This is a pre-implementation review of the proposed *Coach V2* redesign (strict source
> filters + notes exclusion + manifest facets, staged voice via ElevenLabs, staged current-docs/web
> verification via Tavily/Context7). It is **not** an implementation plan to execute — it is gate #2 of
> `ai-dev-workflow` applied *before code*, per the `preplan-adversarial-review` skill. The deliverable
> is a verdict + severity-ranked findings + a guardrail audit + the smallest safe first slice.
> Panel lenses: Principal AI Eng · RAG Architect · Agentic Systems · Eval Eng · Cloud · Learning UX ·
> Voice/Speech UX · Current-docs/Tavily · Privacy/Consent/Governance.
>
> **Grounding.** Findings cite `file:line` from the live repo, read 2026-06-29. Week-2 signatures
> verified against the sibling `../../Week2-RAG_ContextEngineering/genacademy-rag` checkout.

---

## 1. Final verdict

**APPROVE THE DIRECTION — REJECT THE "V2 IN ONE SLICE" FRAMING. Approve-with-major-changes.**
Confidence: high.

The product direction (course-material learning over filtered course evidence, with optional grounded
voice and clearly-separated current-docs) is sound and stays true to the brand. The plan is also
unusually well-staged for voice and web — credit where due. But as written it **bundles six or seven new
system boundaries and at least three new data-egress surfaces into one "v2"** (strict filtering, notes
exclusion, facet manifest, a Week-2 retriever contract change, voice in/out, voice *cloning*,
external-web verification, guest-partner identity metadata). That directly fights the single most
load-bearing guardrail this project has earned: *"Do NOT add new modes/surfaces ahead of the grounded
core… earn each layer"* (`AGENTS.md:126-129`, `AGENTS.md:87-91`), and it **jumps the queue ahead of the
in-flight quality work** that the roadmap calls the binding next order — CONFIRM-band false-refusal
precision and bounded Turn-2 recovery (`roadmap.md:16-31`).

Gating conditions to move from "approve direction" to "approve to build":
1. Cut the first slice to **filters + notes-exclusion only** (Section 8). Voice and web become separate,
   individually-reviewed plans with their own egress/consent gates.
2. Resolve the **two confirmed correctness landmines** (Blocking #1 and #2) before any filter ships.
3. Add the **9 new guardrails** (Section 5) and the **5 new decision records** (Section 6) so a reviewer
   can reject a PR that violates the new contracts — today none of these are enforceable.
4. Treat the notes-excluded index as a **new `corpus_version` with its own recalibration + eval run** —
   never retrofitted onto the existing `7/10` baseline.

---

## 2. Blocking issues (must fix before the relevant slice ships)

**B1 — "Strict filter" leaks the top-scored unselected span. (correctness bug against the contract)**
`foundation.py:45-51`: after `reorder_spans` + truncation, `select_retrieved_spans` **force-injects the
single highest-scored span even if it is a lower-priority / unselected source**. Layer a naive source
filter on top of today's pipeline and a "slides-only / Week-5-only" answer will still re-admit a
transcript or off-week chunk because it had the max score. That violates the plan's own first principle
("answers may cite *only* matching chunks") and the new grounding promise. **Fix:** make the
top-span injection filter-aware (only inject if it passes the active facet filter); add a
filter-faithfulness test that asserts *no* returned/cited span carries a non-matching facet, including
this path.

**B2 — Notes exclusion silently invalidates the calibrated thresholds and the eval baseline.**
STOP=0.40 / CONFIRM=0.85 were calibrated *against the expanded corpus that includes notes*
(`tech-stack.md:103-114`; `settings.py:10-11`), and the constitution's teaching policy literally relies
on *"notes fill gaps"* (`AGENTS.md:71`, `AD-4` `decisions.md:36-43`). `evidence_score` is a **max over
span scores** (`grounding.py:29-30`) and `require_citeable_spans` filters at `>= stop_threshold`
(`grounding.py:46-55`), so removing notes can lower the top score on note-only topics and push them below
STOP → **more refusals, directly worsening the false-refusal metric the roadmap is actively trying to
improve**. **Fix:** treat notes-exclusion as a new `corpus_version`; re-derive per-`source_type` bands on
the new index (tech-stack requires per-source calibration before changing bands, `tech-stack.md:104-109`);
re-run the dev teach-loop eval and report as a **new** result, not a patch to `7/10`. Keep the held-out
`test` split frozen (`gate #4`).

**B3 — The plan's stated retrieval requirement contradicts the reuse contract.**
The plan says strict filters must apply *"before dense/BM25 ranking, not after result selection."* But
Week-2's surface has **no filter argument**: `retriever.py:85 def retrieve(self, query: str)` and
`vectorstore.py:46/132 def query(self, query_embedding, top_k)`. "Filter before ranking" therefore
*requires editing the sibling Week-2 package* — which trips the review-blocker reuse contract
(`AGENTS.md:101-106`, foundation doc §"Reuse contract") and the editable-dependency risk the production
roadmap already flags. You cannot have both "filter before ranking" and "no Week-2 change." **Decide
explicitly** (see Missing Decision M1 and Section 8): start with the Coach-side post-filter (no Week-2
edit), or accept a written Week-2 delta + Week-2-side review + a version pin.

**B4 — Tutor voice cloning has no consent/biometric gate, and "user has course access" is treated as
possibly sufficient.** Course access ≠ consent to clone a person's voice. A voice clone is biometric /
likeness data implicating the tutor's publicity rights and ElevenLabs' voice-cloning terms. **Block all
tutor-voice cloning behind the 5-part gate in Section 10**; default to a standard licensed voice with an
"AI voice" disclosure. This is non-negotiable and must be written as a guardrail before any cloning code.

**B5 — External web egress sends learner text to a third party with no redaction contract.** Sending the
raw learner question (which may contain their name, employer, "at my startup we…") plus corpus snippets
or history to Tavily/Context7 is data egress equivalent in seriousness to the LangSmith decision
(`AD-12`). **Block any external call behind a query-minimization + owner egress-decision contract**
(Section 11, guardrail A4) before the first real adapter.

---

## 3. Important non-blocking concerns

- **Queue-jumping the active priority.** The roadmap's binding next order is false-refusal precision →
  bounded recovery (`roadmap.md:32-52`). V2 should slot in as a *new milestone after* that work, or
  explicitly accept the reprioritization in the roadmap. Don't leave the roadmap claiming one order while
  building another.
- **`guest_partner` as a first-class facet is the wrong shape** (Q2). It is sparse, high-cardinality, and
  bleeds third-party identity into a queryable field. Model `session_type ∈ {core, guest}` + optional
  private `speaker`/`org`. (See M2, guardrail A8.)
- **`corpus/manifest.json` as one hand-maintained JSON will drift** (Q3). Week/session today live only in
  the *filename stem* (`corpus.py:35-39`), so a separate JSON is a second source of truth with no
  enforcement. Make facets **ingest-time, validated against the real corpus tree** (fail the build on an
  orphaned or unlabeled file), and **write facets into chunk metadata at ingest** so retrieval filters
  without a runtime join.
- **Citation labels are reverse-engineered from filenames** (`gradio_app.py` `_friendly_review_target`,
  ~`:886-949`; ids built from filename stems at `corpus.py:35`). Filenames leak content
  ("vendor-confidential-roadmap.pptx", a person's name). Adding guest/partner sources makes a
  privacy-safe *display label decoupled from filename* a prerequisite, not a nicety.
- **STT provider is unspecified.** The voice plan says "microphone → transcript" but ElevenLabs is
  TTS-first. Whose speech-to-text? (ElevenLabs STT, Whisper, or browser `SpeechRecognition`.) Unstated
  decision (M3).
- **Spoken form ≠ cited form.** You don't read `[week3-session1::42]` aloud. TTS needs a citation-stripped
  spoken rendering distinct from the on-screen cited text.
- **Cost/latency caps become real.** Web + voice bill per call on a deployed Space; per-user cost caps
  (already a roadmap pull-in) move from "later" to "before cohort enablement."
- **Over-engineering risk (the MVP-vs-scale trade).** A full filter UI (resource × week × session ×
  guest) over a corpus of *dozens* of files (`corpus/*`: 8 slides, 14 handouts, 9 transcripts) is heavier
  than the corpus warrants. Start with the two facets that earn their keep (resource-type, week).

---

## 4. Missing decisions

- **M1 — Retriever filtering strategy:** Coach-side post-filter (no Week-2 edit) vs Week-2 contract
  extension (`where=`/`filter=` on `query` + BM25 candidate filtering). Recommend post-filter first,
  escalate only on a measured recall gap (mirrors AD-4's own logic). → **AD-14**.
- **M2 — Guest modeling:** `session_type` + `org` vs first-class `guest_partner`. Recommend the former. →
  **AD-18**.
- **M3 — STT provider** and where transcription runs (client vs server vs ElevenLabs). → **AD-16**.
- **M4 — Default web mode:** course-only default + opt-in vs default-on for "eligible" topics. Recommend
  opt-in until routing + redaction + provenance separation are proven. → **AD-15**.
- **M5 — External provider integration:** Tavily MCP vs Python SDK vs abstraction. Recommend a
  provider-neutral `ExternalEvidenceProvider` interface backed first by the **SDK**; defer MCP (a new
  system boundary the constitution says to earn, `AGENTS.md:87-91`). → **AD-15**.
- **M6 — Corpus versioning:** there is no `corpus_version` field today; the plan's "one collection per
  corpus version" needs one, and eval results must be reported against it. → tech-stack + AD-14.
- **M7 — Deployed-backend filtering:** Chroma `where=` vs Pinecone `filter=` differ; the Space is
  Pinecone-capable but Chroma-tested (`README` status). Which backend must support filters at launch?

---

## 5. Guardrail / constitution audit

### Keep unchanged (still binding for v2)
- **Grounded-or-refuse for course facts** (`AGENTS.md:50-52`) — extend, don't weaken.
- **Evidence-bound answerability; STOP deterministic** (`AGENTS.md:53-59`).
- **Citations captured at retrieval, never reconstructed** (`AGENTS.md:66-68`).
- **Held-out `test` split sacred + leak check** (gate #4, `AGENTS.md:39-43`).
- **Pure core / thin view** (`AGENTS.md:92-94`) — *more* important now: voice orchestration and the
  external-evidence provider must live in the framework-free core behind interfaces; audio/web SDKs sit in
  adapters, never imported into core logic.
- **Builder ≠ reviewer (gate #2); evidence before done (gate #3)** (`AGENTS.md:34-38`).
- **Narrowest-reliable-grader / AD-13 ladder.**
- **"Earn each layer / don't add surfaces ahead of the core"** (`AGENTS.md:126-129`) — the discipline
  that keeps v2 from collapsing. Keep it and *apply it to v2 itself*.
- **Don't publish corpus; confirm attribution/permission** (`AGENTS.md:121-125`) — now also covers
  partner identities and voice samples.

### Revise (right direction, too narrow/stale for v2)
- **AD-4 "one retriever, source-prioritized" + "notes fill gaps"** (`decisions.md:36-44`, `AGENTS.md:69-72`,
  `tech-stack.md:14`, `settings.py:8,50`, `README.md:137-139`): revise to *"one retriever,
  **metadata-facet-filterable**, source-prioritized; **notes excluded from learner retrieval** (admin/debug
  only)."* Multi-file edit: drop `note` from the priority tuple everywhere + recalibrate.
- **MINT "no MCP / no A2A / no explicit LangGraph **this week**"** (`AGENTS.md:87-91`,
  `tech-stack.md:154-162`): the "this week" framing is stale post-MVP. Restate as a standing
  earn-the-layer policy with named triggers. Clarify explicitly that **Tavily via SDK is *not* MCP** so a
  reviewer doesn't auto-reject it, and that the no-direct-`langgraph.*` stance still holds unless
  course/web routing or voice pre/post-processing earns an explicit graph (write the decision rather than
  assume — M-level).
- **mission.md "ElevenLabs voice — out of scope / pull-in"** (`mission.md:62`) and
  **roadmap voice = first-in-cut-order** (`roadmap.md:236-238`): revise — voice is now a *staged, governed
  capability*, sequenced after the filter slice and behind consent gates, not a someday-maybe that gets cut
  first.
- **tech-stack "Corpus: notes/slides/handouts/transcripts indexable"** (`tech-stack.md:15`): exclude
  notes; add facet metadata + `corpus_version`.
- **Confidence Bands** (`tech-stack.md:102-114`): add a hard note that the bands must be **recalibrated on
  the notes-excluded, facet-filtered index** before they are trusted.

### Retire
- Little should be *retired* outright — the safety content all survives. Retire only: (a) **"notes fill
  gaps" as a teaching default** (replaced by notes-excluded), and (b) the **Week-3 temporal scoping**
  language ("this week") scattered across AGENTS/tech-stack/decisions, which should be re-dated to "post-MVP
  / v2," not kept as literal week-bound rules.

### Add (new review-blocker guardrails for v2)
1. **Filter = retrieval contract.** With a scope filter set, no retrieved or cited span may carry a
   non-matching facet — *including any top-span fallback*. Filtered-empty → a **filter-aware refusal** that
   names the active filter and offers to broaden; never silently widen.
2. **Notes are not learner evidence.** Excluded from the learner index; re-inclusion is an explicit
   admin/debug flag, never the teaching default.
3. **Provenance separation (course vs external).** External evidence is labeled and cited separately,
   never enters a course citation id, never overrides a course-grounded refusal; conflicts are labeled by
   era.
4. **External egress minimization.** Only a minimized, identity-stripped query may leave the app; no
   corpus text, no PII, no full history. Web is opt-in; an owner decision record authorizes provider +
   scope.
5. **Voice is post-grounding.** Audio is generated only from the final text answer *after* it passes
   retrieval/citation/grounding/refusal. Refusals/ungrounded text are never synthesized by default. Text
   stays canonical.
6. **Biometric/voice data governance.** Raw learner audio, cloned-voice samples, voice IDs, and generated
   audio are private, gitignored, retention-bounded, excluded from traces, never committed.
7. **Tutor voice cloning requires explicit written consent** (5-part gate, Section 10). No clone without
   it; default to a standard licensed voice. Course access ≠ consent.
8. **Guest/partner confidentiality.** Partner identities and guest content are treated like corpus:
   confirm permission before naming a partner in any learner-visible label or committed artifact; org names
   live only in the ignored manifest by default.
9. **Corpus versioning.** Each index carries a `corpus_version`; facet/manifest changes bump it; eval
   results are reported against a named version (a notes-excluded run is not comparable to the
   notes-included `7/10`).

---

## 6. Recommended edits to source-of-truth files

- **AGENTS.md** — §1 add v2 capabilities ("still grounded-first"); §3 revise the "one retriever" bullet
  (facet-filterable + notes-excluded), clarify the MCP-vs-SDK boundary, and add guardrails 1–9 as
  review-blockers; §5 extend "don't publish corpus" to partner names + voice samples; re-date status off
  Week-3.
- **specs/mission.md** — move voice + current-docs from "out of scope/pull-in" into "v2 staged scope behind
  gates"; add the "filters as contract," "notes excluded," "external = supplementary" lines; audience tilt
  unchanged.
- **specs/tech-stack.md** — corpus excludes notes; add facet metadata + `corpus_version`; add rows for
  `ExternalEvidenceProvider` and voice (STT/TTS); recalibration note on bands; Allowed/Forbidden imports —
  Tavily SDK allowed in an adapter, Tavily MCP deferred, web/audio SDKs forbidden in core.
- **specs/roadmap.md** — insert v2 as a milestone *after* the false-refusal/recovery work; reorder so the
  source-filter slice is first; keep voice/web phased; update cut order (voice no longer auto-first-cut but
  still after filters).
- **docs/decisions.md** — add **AD-14** (facet filtering + notes exclusion + Week-2 delta choice),
  **AD-15** (external/current-docs evidence: abstraction, egress minimization, provenance separation, SDK
  before MCP), **AD-16** (voice: text-canonical, post-grounding on-demand+cached TTS, STT choice),
  **AD-17** (tutor voice-cloning consent/biometric governance), **AD-18** (guest/partner metadata +
  confidentiality).
- **docs/foundation-adapter-spec.md** — record the chosen retriever-filter approach and the
  facet-at-ingest write; **docs/genacademy-rag-foundation.md** — record the written delta *iff* Week-2 is
  edited.
- **corpus/README.md** — document manifest/facets, notes-exclusion, and that partner names stay private.
- **README.md "Safety & Privacy"** + **docs/architecture-diagrams.md** — add the filter / provenance /
  voice / web boundaries.
- **preplan-adversarial-review pass tracker** — log this pass (reviewer = Claude/opus, verdict =
  approve-with-major-changes) and re-run a different-model `/codex` pass on the cut-down slice plan.

---

## 7. Recommended edits to the v2 plan

- Split "Key Changes" into **Slice 0 (filters + notes-exclusion)** vs **later slices** (Section 8). The
  current plan's "first implementation slice" is still too big.
- Replace "filters apply before dense/BM25 ranking" with "filters apply to the **over-fetched candidate
  pool before selection**" for Slice 0 (option B), and add the explicit escalation trigger to option A.
- Add B1 (top-span injection must respect the filter) and B2 (recalibration + new corpus_version) as
  acceptance criteria, not afterthoughts.
- Demote `guest_partner` to `session_type` + `org`; demote session-multiselect and guest UI to a later
  slice.
- Make the manifest *ingest-time validated*, not a free-floating JSON.
- For web Phase 1, ship the **`ExternalEvidenceProvider` interface with a null/no-egress provider first**
  (UI toggle + provenance contract + tests) before any real adapter.

---

## 8. Smallest safe first implementation slice

**Slice 0 — Notes-excluded, facet-filterable, grounded text retrieval with a filter-aware refusal.**
Nothing else.

1. Drop `note` from `INDEXABLE_DIRS` (`corpus.py:12`) and `DEFAULT_SOURCE_PRIORITY` (`settings.py:8`) +
   all doc references; re-ingest a fresh `corpus_version` via `scripts/ingest_course_corpus.py`.
2. Add a **typed, validated facet manifest** consumed at ingest; write `week`, `session`, `session_type`,
   `content_kind` (=source_type), optional private `org`, `corpus_version` into chunk metadata. Unit-test:
   every indexable file has exactly one manifest entry (no orphans/unlabeled). Extend
   `scripts/check_eval_leak.py` if the manifest references files.
3. Add a `RetrievalFilters` value object threaded through `Foundation.retrieve(query, filters=None)`
   (backward-compatible default `None`). Implement **option B**: over-fetch (`retrieval_candidate_k`),
   filter candidates by facet **before** `select_retrieved_spans`, and **fix the top-span injection
   (`foundation.py:45-51`) to respect the active filter** (B1).
4. **Filter-aware refusal** distinct from out-of-corpus refusal.
5. **Recalibrate** STOP/CONFIRM per `source_type` on the new index; **re-run the dev teach-loop eval** and
   report as a new `corpus_version` result (B2). Add filter-faithfulness + answerability-under-filter
   tests. `test` split stays frozen.
6. **Minimal UI:** a collapsed *"Scope (optional)"* control with resource-type + week, **all-selected by
   default**. No guest facet UI, no session multiselect yet.
7. Ship through the normal gates: builder ≠ reviewer (`/codex` challenge), `pytest` + `ruff` + leak check
   + one real filtered trace.

### Deferred to later, separate, individually-reviewed slices (in order)
1. Session + guest scope facets + partner-confidentiality handling (after the filter contract is proven).
2. **Web/current-docs:** Phase 1 = UI toggle + answer-provenance contract + `ExternalEvidenceProvider`
   interface with a **null** provider (no real egress) + provenance-separation tests; Phase 2 = Context7
   official-docs adapter (opt-in); Phase 3 = Tavily **SDK** adapter (opt-in, egress decision record,
   query minimization). Each its own plan.
3. **Voice:** Phase 1 = STT decision + push-to-talk → existing grounded text flow → on-demand **cached**
   TTS with a **standard licensed voice** + disclosure label; Phase 2 = streaming; Phase 3 = tutor clone
   **only** after the 5-part consent gate.

---

## 9. Voice UX recommendation

**Text-first, with push-to-talk question entry + an optional "Play answer" control. Not always-on
conversation.** The canonical answer must pass retrieval/citation/grounding/refusal *as text* before any
audio — audio of a hallucination is worse than text of one, and always-on streaming tempts bypassing the
grounding gate and invites latency/barge-in problems. First voice slice = mic → STT → existing grounded
text flow → text answer → optional TTS of the *already-grounded, already-cited* text (citation markers
stripped for the spoken form). Defer WebSocket streaming until grounding, latency, and cost are stable.
Resolve the STT provider (M3) and don't read citation ids aloud.

## 10. Voice-cloning consent / privacy recommendation

**Course access does not imply consent — explicit written consent is always required** (answers Q11–Q12).
Default to a **standard licensed ElevenLabs voice** with an "AI voice — not a recording" label, and treat
tutor cloning as a later, separately-consented enhancement. Block any tutor clone behind all five:
1. **Explicit, written, specific, revocable consent** from the tutor for *this* use (GenAcademy Coach
   answer narration), naming the sample source.
2. **Sample provenance approved by the tutor** (which recordings; tutor controls them; no other
   speakers/learners captured).
3. **Disclosure UX** on every cloned-voice answer ("Synthetic voice of [tutor], AI-generated").
4. **Retention controls** — samples, voice ID, generated audio are private, gitignored, retention-bounded;
   consent withdrawal triggers deletion at ElevenLabs.
5. **Scope limit** — clone used only inside the authed app for answer narration, nothing else.

## 11. Current-docs / web verification recommendation

- **Course corpus is always retrieved first and remains the teaching foundation; web is supplementary.**
- **Opt-in, course-only default** for the first web slice (resist default-on-for-eligible-topics until
  routing + redaction + provenance separation are proven; M4).
- **Routing policy:** allow web only if ALL — question is course-*related* (relevance gate, so it doesn't
  become a general search), learner enabled it, category is eligible (tooling/SDK/API/cloud/security/
  observability/MCP), and the query can be minimized for egress. Prefer **Context7 official docs first**
  for library/API/SDK/cloud; **Tavily SDK** for broader current web only when official docs are
  insufficient. Skip Tavily crawl/map for v2.
- **Never override a grounded refusal.** Course-empty + not opted-in → refuse. Course-empty + opted-in →
  clearly-labeled external answer ("not in course materials; per current docs…"). Both empty → refuse/
  escalate.
- **Conflict handling:** two labeled blocks — *"As taught (Week N, [date]): X"* and *"Current docs
  (checked [date]): Y"* — with a one-line reconciliation when they differ. Separate citation lanes; never
  merge a URL into a course citation id.
- **Integration:** provider-neutral `ExternalEvidenceProvider` in core; SDK-backed; a `null`/disabled
  provider mirrors the existing Mem0 no-op precedent. An **AD-12-style owner egress decision** authorizes
  provider + scope before real calls.

## 12. Test & eval recommendations

- **Filter-faithfulness:** assert no returned/cited span carries a non-matching facet — including the
  top-span injection path (B1).
- **Answerability-under-filter:** labeled (question, correct-facet) set; recall@k and refusal rate with
  filter ON vs OFF; the headline metric is *false refusals introduced by filtering*.
- **Notes-exclusion regression:** re-run the dev teach-loop eval after exclusion + recalibration; report
  as a new `corpus_version` result (not a patch to `7/10`).
- **Recalibration evidence:** per-`source_type` band derivation on the new index.
- **Leak check stays green** with manifest/facets; `test` split frozen.
- **Voice safety test:** TTS is never invoked for refused/ungrounded answers; raw learner audio + generated
  audio never written to tracked paths.
- **Web privacy test:** external lookup receives only a minimized query — no corpus text, no PII, no
  history. **Web citation test:** external citations labeled separately with a `last_checked` date.
  **Conflict test:** disagreement renders both eras explicitly.
- **Regression gates unchanged:** `uv run pytest`, `uv run ruff check`, leak check, one real filtered demo
  trace.

## 13. Cloud / deployment implications

- The HF Space is an **empty-corpus shell**, Chroma-tested with a Pinecone adapter (`README` status).
  Option B (post-filter) is **backend-agnostic** and safest for deploy; option A means implementing both
  Chroma `where=` and Pinecone `filter=` (M7).
- Web + voice add **outbound calls + new secrets** (Tavily, ElevenLabs) to a deployed Space — secret
  management, rate/cost caps, and a **fail-closed-on-external-timeout** path that does not break course-only
  answers. The existing "fail closed when evidence unavailable" pattern (`gradio_app.py` empty-corpus
  handling) is the right precedent to extend.
- Voice adds **latency + cost + audio handling**; on a basic Space, prefer API-based ElevenLabs over local
  models, and keep audio cache on ephemeral storage — **never persist learner audio**.
- **Per-user cost caps** (roadmap pull-in) graduate to a prerequisite before cohort-wide web/voice.
- Don't seed private corpus — *including partner-confidential sessions* — into any public/hosted index.

---

## 14. Direct answers to the review questions (compact)

1. **Strict filtering right?** Right *contract*, but only with a filter-aware refusal + the B1 fix.
   Without them it's a leak and a refusal-spike risk.
2. **guest_partner first-class?** No — `session_type=guest` + private `speaker`/`org`.
3. **manifest.json right layer?** Use an **ingest-time validated** manifest written into chunk metadata,
   not a free-floating JSON; gitignored.
4. **Missing metadata fields?** `week`, `session`, `session_type`, `speaker/org` (private), `date`,
   `corpus_version`, optional `topic_tags`; for web: `provenance`, `source_url`, `last_checked`,
   `official_doc`. Plus a privacy-safe display label decoupled from filename.
5. **Week-2 changes without violating reuse?** Either a written-delta `where=`/`filter=` extension (+ BM25
   candidate filtering, + version pin) or — preferred first — a Coach-side post-filter that needs no
   Week-2 edit. Decide in AD-14.
6. **Evals to prove filters are safe?** Filter-faithfulness, answerability-under-filter (false-refusal
   delta), notes-exclusion regression as a new corpus_version, recalibration, leak check (Section 12).
7. **UI risks?** Over-prominent filters → learners over-narrow → refusals; hidden web-mode → trust/safety;
   strict-empty → must be filter-aware. Default collapsed + all-selected; reuse the existing safe trace
   cards, not raw spans.
8. **First build = filters only or +voice?** Filters only.
9. **Best voice UX?** Push-to-talk question entry + text answer + optional "Play answer." Not always-on.
10. **TTS auto/on-demand/cached?** On-demand, cached by (final-text hash + voice id); never auto, never for
    refusals.
11. **Cloning consent/disclosure/retention?** The 5-part gate (Section 10).
12. **Cloning OK with course access?** No — explicit written consent always required.
13. **Privacy/security risks?** Partner identity (NDA), filename leakage in citations, biometric learner/
    generated audio, trace allow-list creep, web egress of PII, local screenshots (already gitignored —
    keep them so).
14. **Course+current-docs default on?** Opt-in, course-only default, until routing/redaction/provenance
    proven.
15. **Routing policy?** Course-related ∧ learner-enabled ∧ eligible-category ∧ minimizable query; official
    docs before broad web; both-empty → refuse.
16. **Course-era vs current conflict?** Two labeled blocks + one-line reconciliation; separate citation
    lanes.
17. **Tool/source policy?** Staged: Context7 official docs → Tavily SDK search/extract; defer crawl/map;
    domain allow-list toward official sources; attach `last_checked`+URL.
18. **Privacy controls before egress?** Minimized identity-stripped query; no corpus/PII/history; opt-in;
    cached without identifiers; egress logging; owner decision record.
19. **Tavily MCP vs SDK vs abstraction?** Abstraction (`ExternalEvidenceProvider`) backed by the **SDK**
    first; defer MCP.
20. **AGENTS guardrails still binding?** Grounded-or-refuse, evidence-bound answerability, citations at
    retrieval, sacred test split, pure-core/thin-view, builder≠reviewer, evidence-before-done, earn-each-
    layer (Section 5 Keep).
21. **Which to revise?** AD-4/notes-fill-gaps, the "this week" MINT framing, voice scope/cut-order, corpus
    indexable set, confidence bands (Section 5 Revise).
22. **New guardrails needed?** The 9 in Section 5 Add.
23. **Reuse contract still correct?** Yes, with a bounded written-delta exception for metadata filtering
    (AD-14); prefer the no-edit post-filter first.
24. **No-direct-LangGraph still correct?** Yes for Slice 0. Course/web routing + voice pre/post-processing
    *might* earn an explicit graph later — write that decision rather than assume; Tavily-via-SDK does not
    trip the MCP clause.
25. **Smallest safe slice / what's deferred?** Section 8.

---

## 15. Top 3 to do before any code
1. **Cut the milestone to Slice 0** (filters + notes-exclusion) and write **AD-14** (filtering strategy +
   notes exclusion + Week-2 delta choice).
2. **Fix the contract landmines:** filter-aware top-span injection (B1) and the recalibration + new
   `corpus_version` eval plan (B2).
3. **Write the governance guardrails now** (the 9 additions + AD-15/16/17/18) so voice, web, cloning, and
   partner metadata are review-blockable *before* anyone is tempted to build them.
