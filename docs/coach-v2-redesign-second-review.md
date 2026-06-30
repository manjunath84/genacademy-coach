# GenAcademy Coach V2 — Second-Pass Adversarial Review (cohort-ops added)

> **Context.** Second independent pass over the v2 redesign after new **cohort-operations / admin**
> requirements and a clarified **default no-filter, cross-lane synthesis** behavior were added. Prior
> evidence: `docs/coach-v2-redesign-adversarial-review.md` (first pass). Per the
> `preplan-adversarial-review` rule, this pass treats the first review as evidence to challenge, not
> truth. Grounding: repo read 2026-06-29; Week-2 admin verified in the sibling
> `../../Week2-RAG_ContextEngineering/genacademy-rag` checkout. Privacy-clean: no raw corpus, learner
> data, transcripts, secrets, partner names, or screenshots.
> Panel: Principal AI Eng · RAG Architect · Learning UX · Cohort-ops/admin · Eval Eng · Privacy/Consent ·
> Voice · Current-docs/Tavily.

---

## Final verdict

**APPROVE WITH CHANGES.** Confidence: high.

The updated plan is materially stronger than what the first pass reviewed: it already (a) defines a
**default no-filter answer that synthesizes across source lanes** (prompt lines 342–351), (b) keeps the
teaching lens as prompt-level personalization separate from retrieval, and (c) stages cohort-ops into 5
phases that put admin upload last. That staging instinct is correct and lands close to the first review's
"earn each layer" thesis. So this is no longer "reject the v2-in-one-slice framing" — the framing is now
sound. What remains are **four substantive corrections** and **a set of cohort-ops guardrails that don't
exist yet**, all gating before code:

1. **Reframe Slice 0 around the cross-lane-synthesis default**, and fix a real retrieval bug the first
   review missed: the current selection logic **starves non-slide lanes** (Blocking B1).
2. **Keep admin upload out of the first slices** — it is the one cohort-ops feature that can break the
   sacred eval split and silently change learner-visible facts (Blocking B2/B3).
3. **Redesign — do not port — Week-2 admin** (it's FastAPI/Jinja/CSRF; Coach is Gradio) and **fix the
   analytics privacy regression** (Week-2 `usage_log` stores raw questions + email; Coach is hash-only).
4. **Fix the web feature's inverted phase order** (the plan default-enables in Phase 2 before the
   retrieval adapters exist in Phase 3).

---

## Agreements with the first review (still hold, reinforced by cohort-ops)

- **Stage it; don't bundle. Earn each layer.** The cohort-ops requirement *strengthens* this — admin
  upload is a bigger correctness/privacy risk than voice or web, so the discipline matters more, not less.
- **Notes-exclusion is a new `corpus_version` with mandatory recalibration + a fresh eval run**, never a
  patch onto the existing `7/10` (`tech-stack.md:103-114`; `grounding.py:29-30` evidence_score is a max,
  so dropping a lane can push topics below STOP → more refusals). Still blocking.
- **Voice unchanged:** text-canonical, post-grounding, on-demand cached TTS, push-to-talk + play button,
  standard voice default, clone only behind a 5-part written-consent gate.
- **Guest = `session_type` + private `org`, not a first-class `guest_partner` facet**; partner identity
  is corpus-grade confidential.
- **Tavily behind a provider-neutral `ExternalEvidenceProvider`, SDK before MCP; Context7 before Tavily;
  egress minimization; provenance separation; never override a refusal; conflict labeled by era.**
- **Pure core / thin view, builder ≠ reviewer, evidence before done, frozen test split** remain binding.
- **`RetrievalFilters` value object threaded through core/sessions/UI**, backward-compatible default.

## Disagreements with the first review (where this pass corrects it)

1. **Strict filtering was over-weighted.** The first review centered "filters as the retrieval contract"
   and made the top-span-leak a *launch blocker*. With the now-explicit default of **no filter +
   cross-lane synthesis**, filtering is an optional power-user path. The leak (`foundation.py:45-51`) is
   **downgraded to Medium** — it only bites when a filter is active. It must still be fixed before filters
   ship, but it is not a blocker for the default experience.
2. **The first review missed lane-starvation — the bigger retrieval finding.** `select_retrieved_spans`
   (`foundation.py:24-52`) reorders by source priority then truncates to `top_k=5` (`settings.py:48`).
   If the top candidates are all slides, the default answer gets **zero transcript/handout/guest
   evidence** — directly breaking "synthesize across lanes." The default needs **source-balanced selection
   after over-fetch (lane quotas)**, not priority-order-then-truncate. (New Blocking B1.)
3. **The first review missed multi-lane synthesis faithfulness.** Composing across 4 lanes raises
   blend/interpolation risk; the grounding check (`grounding.py:105-107`) and role-keyed single-span
   provenance aren't built for per-lane citation. New eval need.
4. **Web default-on:** first review said opt-in/course-only. The owner wants **default-on when eligible**.
   This pass *partially reverses*: default-on is an acceptable **end state** for a narrow eligible set —
   but only after the adapters + egress-minimization + provenance-separation are proven. (And the plan's
   phase order is inverted; see Blocking B5.)
5. **Recalibration + leak-check are not one-time Slice-0 tasks.** With admin upload coming, the corpus is
   a **moving target**, so both become **standing release gates keyed to `corpus_version`**, run on every
   mutation — not a one-off.

---

## Blocking issues

**B1 — Default cross-lane synthesis is not achievable with the current selection logic (lane starvation).**
`foundation.py:24-52` orders by source priority and truncates to `top_k`; nothing guarantees lane
diversity. Fix: over-fetch (`candidate_k=20` already exists, `settings.py:49`) then **select with per-lane
quotas** so slides/transcript/handout/guest can each contribute when present; **omit or label missing
lanes — never invent one**; attach **per-lane citations**. Also fix the force-inject-top-span
(`foundation.py:45-51`) to respect any active filter (downgraded first-review B1).

**B2 — Notes-exclusion invalidates calibrated bands + the eval baseline.** (Carried, still blocking.)
New `corpus_version`; re-derive per-`source_type` bands; re-run the dev eval as a new result.

**B3 — Admin upload can contaminate the frozen eval split (gate #4 breach) and silently change
learner-visible facts.** Upload mutates the index → changes what the tutor teaches and can overlap the
held-out questions (the build-learnings log already records this exact contamination class). **Admin upload
must not be in Slice 0/1.** When it lands it must: run the **leak check against eval IDs/checksums before
indexing**, treat eval/curriculum as **immutable protected collections** (Week-2 already does this — reuse
it), be **corpus-versioned + pending-review-before-live + rollback-able**, and trigger **recalibration +
eval re-run** as a release gate.

**B4 — Inheriting Week-2 `usage_log` as-is is a privacy regression.** Week-2's usage log stores **raw
question text + user email** (verified in the sibling repo's datastore/usage path), which contradicts the
Coach's hash-only posture (traces store `topic_hash`/`learner_input_hash`, never raw — `gradio_app.py`
`SAFE_*_TRACE_FIELDS`). Cohort analytics must be **aggregate/hashed by construction**: counts, refusal
rate, latency p50/p95 — no raw questions, speech transcripts, or direct identifiers by default.

**B5 — The current-docs phase order is inverted.** The plan **default-enables "Course + current docs" in
Phase 2** but adds the **retrieval adapters in Phase 3** (prompt lines 373–377). You cannot default-enable
a feature whose evidence adapters and egress-redaction don't exist yet. Reorder: contract + null provider →
adapters + egress proof → *then* default-on for a narrow eligible set.

**B6 — Upload is untrusted input.** Malicious/oversized `pptx/docx/pdf`, zip-bomb, path-traversal via
filename. Reuse Week-2's **content-hash storage (no filename trust)** + type/size validation, and require
**permission confirmation for third-party/guest material** before it is learner-visible (corpus-publish
guardrail).

---

## Recommended Slice 0 (learner retrieval only)

Smallest safe first slice — **default cross-lane synthesis + optional narrowing, text only, no admin UI,
no voice, no web**:

1. **Notes excluded.** Drop `note` from `corpus.py:12` `INDEXABLE_DIRS` and `settings.py:8`
   `DEFAULT_SOURCE_PRIORITY`; re-ingest a fresh `corpus_version` via `scripts/ingest_course_corpus.py`.
2. **Ingest-time validated facet manifest** → write `week`, `session`, `session_type`, `content_kind`
   (=source_type), optional **private** `org`, `corpus_version` into chunk metadata. Unit test: every
   indexable file has exactly one manifest entry (no orphans/unlabeled). Extend `check_eval_leak.py`.
3. **Default cross-lane synthesis retrieval (B1):** over-fetch then **lane-quota selection**; lanes are
   evidence-bound (each shown lane carries its own citations); missing lanes omitted/labeled, never
   invented. This is the headline behavior, not strict filtering.
4. **Optional `RetrievalFilters` narrowing** (resource-type + week), **default = all selected**;
   filter-aware refusal distinct from out-of-corpus refusal; top-span injection respects the active filter.
5. **Recalibrate** bands per `source_type` on the new index; **re-run dev eval** as a new `corpus_version`
   result; add **lane-coverage**, **multi-lane faithfulness**, and **filter-faithfulness** tests; frozen
   test split + green leak check.
6. **Teaching lens stays prompt-level only** (low-code / code-heavy / bridge) — *not* retrieval-aware;
   bridge as the default for uncertain learners is reasonable.
7. **Minimal UI:** default no-filter answer with labeled lanes; a collapsed *"Scope (optional)"* control
   (resource-type + week, all-selected).

> Note: the **facet inventory data** (what weeks/sessions/lanes exist) is a Slice 0 dependency — you need
> it to populate filter options — but the **admin inventory UI** is Slice 1, not Slice 0.

## Recommended Slice 1+ (sequence)

- **Slice 1 — Read-only cohort-ops (low risk, high value):** corpus inventory + statistics over the
  manifest/index (per-lane / per-week chunk counts, indexed status, `corpus_version`), surfaced in the
  existing Gradio admin tab. Reuses `store.get_all_chunks()` and Week-2 `list_documents` /
  `get_chunks_for_doc`. De-risks the filter UI and replaces the Space's empty-corpus blindspot. **Read-only
  — no mutation.**
- **Slice 2 — Cohort access management:** invite codes + account lifecycle, reusing the Week-2 scheme
  (`id.secret` bearer token, secret hashed at rest, role-bound, single-use, expiring, revocable, atomic
  redeem) on top of the existing `CoachAuth` (`web/auth.py` already reuses Week-2 bcrypt + admin-only
  `create_user`/`list_users`).
- **Slice 3 — Current-docs/web** (reordered, B5): contract + UI toggle + `ExternalEvidenceProvider` null
  provider + provenance-separation tests → Context7 official-docs adapter (opt-in) → Tavily SDK adapter
  (opt-in, egress decision record, query minimization) → **then** default-on for a narrow eligible set.
- **Slice 4 — Voice:** STT decision + push-to-talk → grounded text → on-demand cached TTS with a **standard
  licensed voice** + disclosure → streaming → tutor clone **only** after the 5-part consent gate.
- **Slice 5 — Admin upload (gated, late):** corpus-versioned, pending-review, leak-gated, recalibrated,
  file-hardened, permission-checked, rollback-able. The most powerful and most dangerous feature.
- **Slice 6 — Cohort analytics (last):** redacted/aggregate only (B4).

> The in-flight false-refusal-precision + bounded-recovery work (`roadmap.md:16-52`) still sits ahead of
> all of this, or the roadmap must explicitly record the reprioritization.

---

## Cohort operations / admin recommendation

**Reuse the Week-2 *security primitives*; redesign the *UI*; defer the *mutation* features.** Week-2's
admin is FastAPI routes + Jinja templates (`admin_documents.html`, `admin_invites.html`,
`admin_dashboard.html`) + CSRF — **Coach is Gradio, so the templates/routes do not port**; the hard-won
*safety lessons* do.

| Week-2 capability | Verdict for Coach v2 |
|---|---|
| bcrypt auth + admin/member roles | **Reuse** (already done — `web/auth.py`). |
| Invite codes (`id.secret`, hashed, role-bound, single-use, expiring, revocable, atomic redeem) | **Reuse the scheme** (Slice 2); Coach lacks it today. |
| Content-hash upload storage (no filename trust) + provenance fields + corpus-mutation lock + protected eval/curriculum collections | **Reuse the safety mechanics** when upload lands (Slice 5). |
| Admin upload / delete / reindex (FastAPI `UploadFile`) | **Redesign + defer** to Slice 5; decide Gradio-bounded vs the planned FastAPI/HTMX boundary (`production-roadmap.md`). |
| Read-only `list_documents` / inventory | **Reuse data, redesign UI** in the Gradio admin tab (Slice 1). |
| Usage dashboard (queries, refusal/fallback rate, latency p50/p95, top questions, by-day) | **Redesign** — keep aggregates, **drop raw question/email capture** (B4). |
| `usage_log` raw question + email; thumbs feedback tied to raw question | **Drop/redesign** to hashed/aggregate until a redaction decision (B4). |
| FastAPI + Jinja templates + CSRF screens | **Drop** as UI; the planned FastAPI/HTMX boundary, if adopted, is a separate AD. |
| SQLite auth/invite store | **Keep for cohort/demo**; record a future Postgres/external-auth boundary for real rollout. |

**Slice-0 inclusion (Q2):** No. Keep Slice 0 purely learner retrieval. Read-only inventory is Slice 1.
**Admin upload separate from filters (Q3):** Yes, emphatically — read-path learner narrowing vs write-path
corpus mutation are orthogonal and must not be coupled. A heavy cross-cutting concern: **every corpus
mutation re-opens B2/B3** (recalibration + leak check), so upload carries a release-gate, not a button.

## Voice recommendation

Unchanged and affirmed: **text is canonical; audio is generated only after retrieval/citation/grounding/
refusal pass; never synthesize refusals.** Push-to-talk question entry + optional "Play answer";
**on-demand, cached by (final-text hash + voice id)**; **standard licensed voice by default** with an
"AI voice — not a recording" label. **Tutor cloning blocked behind the 5-part gate** (explicit written
revocable consent for this use · approved sample provenance · per-answer disclosure · retention controls +
deletion on withdrawal · scope limited to in-app narration). Course access ≠ consent. Resolve the **STT
provider** (unstated). Raw learner audio, samples, voice IDs, generated audio: private, gitignored,
retention-bounded, excluded from traces, never committed.

## Current-docs / Tavily recommendation

Affirm the first review **plus**: default-on-when-eligible is an acceptable **target** (reversing the
first review's strict opt-in) — but **reorder the phases (B5)**: contract + null provider → Context7
official-docs adapter → Tavily SDK adapter with egress minimization + provenance separation → **then**
default-on for a **narrow, explicitly-listed** eligible set (SDK/API/cloud/security/observability/MCP,
fast-drift), with a visible per-answer mode indicator and one-click disable. Hard rules: official docs
(Context7) before broad web (Tavily SDK, defer MCP); **minimized identity-stripped query only**; **external
evidence never enters the index, `corpus_version`, or the eval surface** (it is not course-grounded);
never override a course refusal; conflicts rendered as two era-labeled blocks with separate citation lanes;
an AD-12-style **owner egress decision** authorizes provider + scope before real calls.

---

## Guardrail / constitution edits

Carry the **first review's 9 additions**, and add cohort-ops guardrails:

- **G-update (filter contract):** rewrite to lead with the default — *"Default learner Q&A selects all
  approved lanes and synthesizes across them; every shown lane is evidence-bound and never invented.
  Optional filters narrow; with a filter set, no retrieved/cited span may carry a non-matching facet
  (including any top-span fallback); filtered-empty → filter-aware refusal, never silent widening."*
- **G10 — Corpus mutations are versioned + gated.** Any index change (notes-exclusion, reingest, admin
  upload) bumps `corpus_version` and must pass leak-check + recalibration + dev-eval, and go through
  pending-review, before becoming learner-visible.
- **G11 — Protected collections are immutable to admin.** Eval/curriculum/held-out splits cannot be
  deleted or overwritten by any admin action (reuse Week-2 protection).
- **G12 — Uploads are untrusted input.** Content-hash storage, no filename trust, type/size validation,
  and third-party/guest permission confirmation before learner-visible.
- **G13 — Cohort analytics are privacy-safe by construction.** Aggregate/hashed only; no raw learner
  questions, speech transcripts, or direct identifiers in dashboards/logs by default (supersedes inheriting
  Week-2 `usage_log`).
- **G14 — Invite codes** follow the Week-2 scheme (hashed at rest, role-bound, single-use, expiring,
  revocable); never committed or logged in plaintext.

**Keep / Revise / Retire** from the first review stand; additionally **revise** `roadmap.md` to capture the
full cohort-ops surface (today it has only a single "admin upload" pull-in line) and **revise** the
production-roadmap's FastAPI/HTMX boundary note to own the admin-UI decision.

## Specific files that should be updated before build

- `AGENTS.md` §1/§3/§5 — v2 capabilities; the G-update + G10–G14 as review-blockers; analytics privacy;
  partner/voice-sample confidentiality.
- `specs/mission.md` — default cross-lane synthesis; lens-as-personalization; cohort-ops in scope (staged).
- `specs/tech-stack.md` — notes excluded; facet metadata + `corpus_version`; lane-quota selection policy;
  `ExternalEvidenceProvider` + voice rows; recalibration-per-version note; analytics-redaction rule.
- `specs/roadmap.md` — insert the Slice 0→6 sequence; capture the full cohort-ops surface; web phase
  reorder; voice phasing; reconcile with the in-flight false-refusal/recovery order.
- `docs/decisions.md` — new ADs: **AD-14** facet filtering + notes exclusion + lane-quota synthesis +
  Week-2 retriever-delta choice; **AD-15** external-evidence (abstraction, egress, provenance, SDK-before-
  MCP, default-on-after-proof); **AD-16** voice; **AD-17** tutor-clone consent/biometric; **AD-18** guest/
  partner metadata; **AD-19** cohort-ops product shape (reuse security primitives, redesign UI, Gradio-vs-
  FastAPI admin boundary, defer upload); **AD-20** corpus-versioning + mutation gating + analytics privacy.
- `docs/foundation-adapter-spec.md` / `docs/genacademy-rag-foundation.md` — record the retriever-filter +
  lane-quota approach and (iff Week-2 is edited) the written delta.
- `corpus/README.md`, `README.md` Safety & Privacy, `docs/architecture-diagrams.md` — new surfaces.
- `docs/INDEX.md` — link both reviews.

## Test / eval gates before build

First review's matrix **plus**:
- **Lane-coverage:** default synthesis surfaces multiple lanes when present (no starvation, B1).
- **Multi-lane faithfulness:** each lane-labeled claim resolves to that lane's retrieved span; no invented
  lanes; per-lane citations attached.
- **Filter-faithfulness:** with a filter set, no returned/cited span (incl. top-span path) carries a
  non-matching facet.
- **Notes-exclusion regression + per-version recalibration:** bands re-derived and dev eval re-run per
  `corpus_version`.
- **Upload leak gate:** uploaded content checked against eval IDs/checksums before indexing; protected
  collections immutable; corpus-version + rollback recorded.
- **Analytics redaction:** dashboards/logs contain no raw questions, transcripts, or identifiers.
- **Voice safety/privacy + current-docs egress/citation/conflict** tests (as first review).
- Regression gates unchanged: `uv run pytest`, `uv run ruff check`, leak check, one real filtered + one
  real default-synthesis demo trace. Frozen test split.

---

## Direct answers to the 10 questions
1. **Smallest safe first slice now?** Slice 0 = notes-excluded, **default cross-lane synthesis** + optional
   resource-type/week narrowing, text only. No admin UI, no voice, no web.
2. **Slice 0 include read-only inventory/admin?** No. Facet **inventory data** is a Slice-0 dependency;
   the **admin inventory UI** is Slice 1.
3. **Admin upload separate from filters?** Yes — orthogonal (read-path vs write-path); upload carries a
   release-gate, not a button.
4. **Week-2 admin reuse/redesign/defer/drop?** Reuse security primitives (auth, invite scheme, content-hash
   storage, mutation lock, protected collections); redesign the UI (Gradio, not FastAPI/Jinja) and the
   analytics (hashed/aggregate); defer upload/reindex + analytics; drop raw-question `usage_log`.
5. **Docs to change before implementation?** AGENTS/mission/tech-stack/roadmap + AD-14…20 + foundation
   specs + corpus/README + README Safety & Privacy + INDEX (see above).
6. **Does the first review still hold?** Thesis yes, reinforced; specifics updated — B1(strict-filter
   leak) downgraded, lane-starvation promoted to blocking, web default-on partially reversed, recalibration
   becomes a standing per-version gate.
7. **Where I disagree with the first review?** The 5 points in "Disagreements" (over-weighted strict
   filtering; missed lane-starvation; missed multi-lane faithfulness; web default-on; one-time vs standing
   recalibration).
8. **Top privacy + eval risks?** Upload→eval-split contamination; raw-question analytics; multi-lane
   synthesis faithfulness/invention; recalibration-on-every-mutation; guest/partner permission; voice
   biometric data.
9. **Tests/evals to prove safe?** The gate list above (lane-coverage, multi-lane faithfulness,
   filter-faithfulness, per-version recalibration, upload leak gate, analytics redaction, voice/web tests).
10. **Final roadmap sequence?** Slice 0 retrieval → 1 read-only inventory/stats → 2 invites/accounts →
    3 web (null→Context7→Tavily→default-on) → 4 voice (standard→stream→clone) → 5 admin upload (gated) →
    6 redacted analytics; behind the in-flight false-refusal/recovery work unless explicitly reprioritized.

## Top 3 to do before any code
1. **Reframe Slice 0 around cross-lane synthesis and fix lane-starvation (B1)** + write **AD-14**.
2. **Write the cohort-ops guardrails (G10–G14) and AD-19/AD-20** so admin upload, mutation gating, and
   analytics privacy are review-blockable *before* anyone builds them.
3. **Fix the web phase order (B5)** and **redesign Week-2 analytics to hashed/aggregate (B4)** in the plan.
