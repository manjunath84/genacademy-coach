# GenAcademy Coach - Architecture & Agentic-Flow Diagrams

> **Purpose:** portfolio-ready architecture diagrams for the grounded tutor, deterministic pull-ins, and
> privacy boundaries.
> **Status:** shipped/planned map. The CLI + local Gradio teach/quiz/Skill-Gap surfaces are shipped.
> The private Hugging Face Space is
> a live deployment shell with no private corpus uploaded.
> Direct voice, admin upload, cross-session memory, and mock interview remain planned pull-ins.
> The constitution (`../AGENTS.md`, `../specs/*`, `docs/decisions.md`) is canonical.

## The Spine

> My agent helps a **Gen Academy cohort learner** master a course concept in a **web chat**, replacing
> the re-watch-the-lecture-and-hope-it-clicks loop. It retrieves citeable course evidence, explains in
> the learner's style and chosen teaching lens, checks understanding, and when the learner stumbles,
> chooses a different explanation strategy at runtime. The same learner can switch between
> no-code/low-code, code-heavy, or bridge explanations for the same topic. It hands off to a human
> mentor when it cannot cite the answer. The current dated dev evidence is `7/10` overall and `7/8`
> teachable, with safe refusals preserved instead of forcing unsupported answers.

| Framework field | Coach |
|---|---|
| **Agent goal** | Teach one course concept until the learner can pass a grounded check-question. |
| **Where used** | Local Gradio web chat and CLI for teach/quiz/Skill-Gap; Hugging Face shell for deployment proof; ElevenLabs voice is a later pull-in over the same engine. |
| **Steps** | teach: intake -> retrieve -> explain -> check -> grade -> runtime decide -> update profile -> loop/report. Quiz and Skill-Gap compose the same retrieval, grounding, trace, and refusal primitives. |
| **Tools** | Teach tools: `retrieve_course_corpus` (READ), `generate_check_item` (Nebius), `grade_understanding`, `update_profile`, `write_trace`, `escalate_to_mentor` (WRITE/HITL). Deterministic pull-ins reuse the same retrieval, grading, trace, and review-queue primitives. |
| **State** | Within-session learner profile: style, track lens, optional bridge source, known, struggled, coverage, turn budget, transcript. |
| **Never do** | Answer from model priors, fabricate citations, index held-out eval questions, or silently skip failure handling. |
| **HITL** | Refuse and write a review-queue entry when confidence is low, evidence is missing, or the learner flags an issue. |
| **Failure handling** | Retry/tool validation, confidence thresholds, source fallback, human escalation, stop/progress guard. |
| **Success measure** | Dated dev eval and redacted traces; deterministic grounded grader; citations resolve to retrieved spans; held-out `test` split remains unused. |

## 1. Product Surface and Deployment Boundary

The shipped application surface is local-first because it runs against the private course corpus. The Hugging
Face Space proves deployability, but it intentionally stays a shell until a public-safe corpus subset is
approved and uploaded.

```mermaid
flowchart LR
    Learner["Learner / reviewer"]

    subgraph Local["Local app with private corpus"]
        Gradio["Local Gradio UI\nTeach · Quiz · Skill-Gap (PR #28)"]
        CLI["CLI entry points\nteach · quiz · skill-gap"]
    end

    subgraph Space["Private Hugging Face Space"]
        Shell["Deployment shell\nHTTP 200 + empty-corpus notice"]
        NoCorpus["No private corpus/index uploaded"]
    end

    subgraph Core["Shared Coach core"]
        Teach["Teach agent"]
        Quiz["Grounded quiz"]
        SkillGap["Skill-Gap diagnosis"]
    end

    Learner --> Gradio
    Learner --> CLI
    Learner -. smoke only .-> Shell
    Gradio --> Core
    CLI --> Core
    Shell --> NoCorpus
    Shell -. same app shell, no private data .-> Core
```

## 2. System Architecture

One LangChain `create_agent` loop handles the adaptive teach mode on LangGraph's internal runtime.
Quiz Mode and Skill-Gap Diagnosis are deterministic pull-ins over the same retrieval, grounding, trace,
and refusal primitives. Most tools read; only escalation/review-queue writes.

```mermaid
flowchart TD
    UI["Thin views\nGradio + CLI"]

    subgraph Modes["Mode layer"]
        TeachMode["Teach mode\nagentic runtime decision"]
        QuizMode["Quiz mode\ndeterministic assessment"]
        SkillGapMode["Skill-Gap mode\ndeterministic next-step report"]
    end

    subgraph Agent["Teach Agent - LangChain create_agent"]
        Reason["Model chooses\nnext_action + strategy"]
        Profile[("Within-session profile")]
    end

    subgraph SharedCore["Shared safety/core primitives"]
        R["retrieve_course_corpus"]
        Ground["evidence_score + evidence_band\nrequire_citeable_spans"]
        Gen["generate_check_item / quiz item\nNebius provider"]
        Grade["Python deterministic grading"]
        Trace["Typed redacted trace writers"]
        Esc["escalate_to_mentor\nreview_queue.jsonl"]
    end

    subgraph Foundation["Week-2 genacademy-rag foundation"]
        Corpus["Extended course vectorstore\nChroma local · Pinecone hosted\nslides · handouts · notes · transcripts"]
        Provider["Nebius/OpenAI-compatible provider"]
        Eval["Eval harness + split manifest\nheld-out test never indexed"]
    end

    UI --> Modes
    Modes --> TeachMode
    Modes --> QuizMode
    Modes --> SkillGapMode

    TeachMode --> Reason
    Reason <--> Profile
    Reason --> R
    Reason --> Gen
    Reason --> Grade
    Reason --> Trace
    Reason --> Esc

    QuizMode --> R
    QuizMode --> Ground
    QuizMode --> Gen
    QuizMode --> Grade
    QuizMode --> Trace

    SkillGapMode --> Trace
    SkillGapMode --> R
    SkillGapMode --> Ground
    SkillGapMode --> Esc

    R --> Corpus
    Gen --> Provider
    Eval -. dev regression only .-> Modes
```

## 3. Adaptive Teach Loop

The MVP is agentic only if the model chooses the next action from observations. Python enforces
thresholds, schema, citation presence, max turns, and stop conditions.

```mermaid
flowchart TD
    Start([Learner picks concept + teaching lens]) --> Retrieve["Retrieve citeable span\nslides/handouts first"]
    Retrieve --> Ground{"Grounded?\nscore + citation present"}
    Ground -->|no| Refuse["Refuse + escalate"]
    Ground -->|yes| Explain["Explain in learner style + lens"]
    Explain --> Check["Ask grounded check-question"]
    Check --> Grade["Deterministic grounded grade"]
    Grade --> Decide{"MODEL CHOOSES\nnext_action + strategy"}
    Decide -->|advance| Known["Update known[]"]
    Decide -->|re_explain_differently| Struggle["Update struggled[]"]
    Decide -->|drill| Drill["Ask smaller grounded drill"]
    Decide -->|refuse_escalate| Refuse
    Decide -->|stop| Report["Session report"]
    Struggle --> ReExplain["New strategy:\nanalogy / simpler steps / contrastive example"]
    ReExplain --> Check
    Drill --> Check
    Known --> Continue{"Budget and coverage left?"}
    Continue -->|yes| Retrieve
    Continue -->|no| Report
```

## 4. Teach Agent Orchestration

```mermaid
sequenceDiagram
    actor L as Learner
    participant A as create_agent
    participant P as Profile
    participant R as Retriever
    participant N as Nebius/provider
    participant T as Trace

    L->>A: "I don't get attention"
    A->>P: Read style, track lens, known, struggled
    A->>R: retrieve_course_corpus("attention", preferred_sources=["slide","handout"])
    R-->>A: Spans + citation IDs + scores
    alt citeable
        A->>L: Grounded explanation with citation
        A->>N: generate_check_item(retrieved_span)
        N-->>A: Check item + answer key
        A->>L: Check-question
        L->>A: Partial/wrong answer
        A->>A: Choose next_action + strategy from observation
        A->>T: Write structured trace turn
    else not citeable
        A->>L: Refuse + escalate
        A->>T: Write refusal trace
    end
```

## 5. Grounded Quiz Mode Flow

Quiz Mode is a deterministic assessment pull-in. The model may draft a multiple-choice item from a
retrieved span, but Python pins the citation, validates grounding, owns the answer key, and grades the
selected option.

```mermaid
flowchart TD
    Topic["Topic + question count"] --> Retrieve["Retrieve raw spans"]
    Retrieve --> Score["Compute evidence score/band\nbefore filtering"]
    Score --> Citeable{"Any citeable span?"}
    Citeable -->|no| Refuse["Refuse quiz + queue review"]
    Citeable -->|yes| Draft["Provider drafts MCQ\nwithout citation authority"]
    Draft --> Pin["Python pins citation_id\nfrom retrieved span"]
    Pin --> Validate{"Grounded content?\ncorrect option + answer + rationale + keywords"}
    Validate -->|no| NextSpan{"More spans?"}
    NextSpan -->|yes| Draft
    NextSpan -->|no| Refuse
    Validate -->|yes| Question["QuizQuestion"]
    Question --> Grade["Python deterministic grade\nselected option == answer key"]
    Grade --> Trace["QuizTraceRow allow-list\ntopic_hash · IDs · scores · booleans"]
    Trace --> UI["UI shows score + metadata\nquestion text hidden by default"]
```

## 6. Skill-Gap Diagnosis Flow

Skill-Gap Diagnosis is the standout workflow. It composes existing evidence instead of adding a memory
provider or a second agent loop: quiz grades, teach trace struggles, and review-queue events produce a
ranked gap list; each gap then retrieves citeable next-step material or refuses/escalates.

```mermaid
flowchart TD
    SourceIDs["Source session IDs"] --> Read["Read local teach traces\nquiz traces · review_queue"]
    Read --> Signals["Derive deterministic signals\nquiz misses · struggled[] · refusals"]
    Signals --> Rank["Rank gaps\nNO LLM mastery grading"]
    Rank --> Retrieve["Retrieve review material per gap"]
    Retrieve --> Citeable{"Citeable review span?"}
    Citeable -->|yes| Plan["Cited next-step plan"]
    Citeable -->|no| Escalate["refuse_escalate + review queue"]
    Plan --> Trace["SkillGapTraceRow allow-list\ntopic_hash · counts · scores · actions"]
    Escalate --> Trace
    Trace --> UI["UI report\nfriendly gap labels + source location"]
    Trace -. exact IDs for audit only .-> JSON["Collapsed metadata JSON"]
```

## 7. Local UI Flow and Redaction Boundary

The UI is a thin view. It makes the grounded tutor legible without moving private data into public
surfaces or adding web-framework imports to the core.

```mermaid
flowchart TD
    Gradio["Local Gradio app\nshare=false"]
    TeachTab["Teach tab\npreset -> run teach"]
    QuizTab["Quiz tab\nquestion text hidden by default"]
    SkillGapTab["Skill-Gap tab\nsource sessions -> diagnosis"]
    Core["Pure Coach core"]
    SafeTrace["safe_trace_rows allow-list"]
    Cards["Readable trace cards\ncounts · scores · actions"]
    JSON["Collapsed metadata JSON\nexact IDs for audit"]
    Private["Never publish\nraw spans · eval prompts · secrets · quiz text"]

    Gradio --> TeachTab
    Gradio --> QuizTab
    Gradio --> SkillGapTab
    TeachTab --> Core
    QuizTab --> Core
    SkillGapTab --> Core
    Core --> SafeTrace
    SafeTrace --> Cards
    SafeTrace --> JSON
    Core -. blocked .-> Private
```

## 8. Failure Handling

```mermaid
flowchart TD
    Signals["Signals: retrieval score + citation present + tool status"] --> Band{"Confidence band"}
    Band -->|STOP| Refuse["Refuse + review_queue.jsonl"]
    Band -->|CONFIRM| Caveat["Ask clarifying/drill or queue for review"]
    Band -->|PROCEED| Teach["Teach/check/grade"]

    ToolErr["Tool error/timeout"] --> Retry["Retry policy"]
    BadItem["Ungrounded check item"] --> Validation["Tool validation"]
    ThinTopic["Thin source coverage"] --> Fallback["Fallback source policy"]
    Loop["Stalled/runaway"] --> Stop["Stop/progress guard"]
```

## 9. State

```mermaid
flowchart TD
    subgraph Session["MVP: within-session profile"]
        Style["style"]
        Track["track_lens"]
        Bridge["bridge_from"]
        Known["known[]"]
        Struggled["struggled[]"]
        Coverage["coverage + turn budget"]
        Transcript["transcript"]
    end

    subgraph Later["Pull-ins"]
        Mem0["cross-session memory"]
        Voice["ElevenLabs voice"]
        Admin["admin uploads"]
    end

    Session -. promote after MVP .-> Later
```

## 10. Corpus and Eval Boundary

```mermaid
flowchart TD
    subgraph Indexed["Indexed course corpus"]
        N["notes/"]
        S["slides/"]
        H["handouts/"]
        T["transcripts/"]
    end

    Ingest["Week-2 chunker + embedder + vectorstore schema"]
    Indexed --> Ingest --> Retriever["retrieve_course_corpus"]

    subgraph NeverIndexed["Never indexed"]
        Q["corpus/eval-questions/\nreal chat questions"]
    end

    Q --> Split["seed/dev/test manifest + checksums"]
    Split --> Test["held-out test loads only inside eval"]
    Test -. blocked from prompts/index/local examples .-> Retriever
```

## 11. Modes and Pull-Ins

```mermaid
flowchart LR
    MVP["SHIPPED: text teach loop\nCLI + local Gradio"]
    MVP --> Quiz["SHIPPED PULL-IN: quiz mode"]
    Quiz --> SkillGap["SHIPPED CORE: skill-gap diagnosis\nCLI + PR #28 local Gradio"]
    SkillGap --> Interview["ROADMAP: mock interview\nopen answer -> cited grading -> follow-up -> report"]
    MVP --> Admin["ROADMAP: admin upload"]
    MVP --> Voice["ROADMAP: ElevenLabs voice"]
    MVP --> Memory["ROADMAP: cross-session memory"]

    style MVP fill:#EAFF00,stroke:#0F1419,stroke-width:2px
```

## 12. Deliverable Mapping

| Handout requirement | Architecture answer |
|---|---|
| Multi-step task | Teach loop from intake through report. |
| Tools | Retriever, Nebius item generation, grader, profile update, trace writer, escalation. |
| State | Within-session profile. |
| Human-in-the-loop | Refusal + review queue. |
| Tool failure / recovery | Retry, validation, fallback, confidence bands, escalation, stop guard. |
| How it worked | Dev eval, redacted traces, local UI screenshots, Skill-Gap evidence, and honest numbers; held-out `test` remains unused. |
| Assessment/gap diagnosis pull-ins | Quiz and Skill-Gap diagrams show deterministic grading/ranking over shared grounded primitives, not second agent loops. |
| Architecture diagram | Diagrams 1-11 in this file. |
