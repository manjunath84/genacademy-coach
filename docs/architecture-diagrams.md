# GenAcademy Coach - Architecture & Agentic-Flow Diagrams

> **Purpose:** the handout-required architecture diagram and the visual spine for the Google Doc/video.
> **Status:** shipped/planned map. The CLI + local Gradio teach/quiz surfaces are shipped; direct voice,
> admin upload, cross-session memory, and mock interview remain planned pull-ins.
> The constitution (`../AGENTS.md`, `../specs/*`, `docs/decisions.md`) is canonical.

## The Spine

> My agent helps a **Gen Academy cohort learner** master a course concept in a **web chat**, replacing
> the re-watch-the-lecture-and-hope-it-clicks loop. It retrieves citeable course evidence, explains in
> the learner's style and chosen teaching lens, checks understanding, and when the learner stumbles,
> chooses a different explanation strategy at runtime. The same learner can switch between
> no-code/low-code, code-heavy, or bridge explanations for the same topic. It hands off to a human
> mentor when it cannot cite the answer, and I know it works when held-out learner-sim scenarios reach a
> correct grounded answer 8 times out of 10.

| Framework field | Coach |
|---|---|
| **Agent goal** | Teach one course concept until the learner can pass a grounded check-question. |
| **Where used** | Local Gradio web chat and CLI for the MVP; ElevenLabs voice is a pull-in over the same engine. |
| **Steps** | intake -> retrieve -> explain -> check -> grade -> runtime decide -> update profile -> loop/report. |
| **Tools** | `retrieve_course_corpus` (READ), `generate_check_item` (Nebius), `grade_understanding`, `update_profile`, `write_trace`, `escalate_to_mentor` (WRITE/HITL). |
| **State** | Within-session learner profile: style, track lens, optional bridge source, known, struggled, coverage, turn budget, transcript. |
| **Never do** | Answer from model priors, fabricate citations, index held-out eval questions, or silently skip failure handling. |
| **HITL** | Refuse and write a review-queue entry when confidence is low, evidence is missing, or the learner flags an issue. |
| **Failure handling** | Retry/tool validation, confidence thresholds, source fallback, human escalation, stop/progress guard. |
| **Success measure** | Held-out chat-question scenarios; deterministic grounded grader; citations resolve to retrieved spans. |

## 1. System Architecture

One `create_agent` loop on LangGraph's internal runtime, one source-prioritized retriever over the
extended Week-2 corpus, and local trace/eval artifacts. Most tools read; only escalation writes. The
diagrams below label the architecture; current shipped surfaces are CLI + local Gradio teach/quiz, while
voice, memory, admin upload, and mock interview remain planned.

```mermaid
flowchart TD
    User["Cohort learner"]
    Intake["Intake: topic · style · track lens"]

    subgraph Agent["Coach Agent - LangChain create_agent"]
        Reason["REASON: choose next_action + strategy"]
        Profile[("Within-session profile")]
        Trace["Local JSON trace + CLI pretty print"]
    end

    subgraph Tools["Tools"]
        R["retrieve_course_corpus(query, preferred_sources)"]
        Gen["generate_check_item(span) - Nebius"]
        Grade["grade_understanding(answer, key, citation)"]
        Update["update_profile"]
        Esc["escalate_to_mentor - WRITE"]
    end

    subgraph Corpus["Extended Week-2 collection"]
        Slides["slides - primary"]
        Handouts["handouts - primary"]
        Notes["notes - gap fill"]
        Transcripts["transcripts - support/fallback"]
    end

    Eval["Held-out chat-question eval - never indexed"]
    Mentor["Human mentor / review queue"]
    LangSmith["LangSmith traces - optional"]

    User --> Intake --> Reason
    Reason <--> Profile
    Reason --> R
    R --> Slides
    R --> Handouts
    R --> Notes
    R --> Transcripts
    Reason --> Gen
    Reason --> Grade
    Reason --> Update
    Reason --> Esc
    Reason --> Trace
    Trace -. optional export/debug .-> LangSmith
    Esc --> Mentor
    Eval -. eval only .-> Reason
    Reason --> User
```

## 2. Adaptive Teach Loop

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

## 3. One ReAct Turn

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

## 4. Failure Handling

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

## 5. State

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

## 6. Corpus and Eval Boundary

```mermaid
flowchart TD
    subgraph Indexed["Indexed course corpus"]
        N["notes/"]
        S["slides/"]
        H["handouts/"]
        T["transcripts/"]
    end

    Ingest["Week-2 chunker + embedder + Chroma schema"]
    Indexed --> Ingest --> Retriever["retrieve_course_corpus"]

    subgraph NeverIndexed["Never indexed"]
        Q["corpus/eval-questions/\nreal chat questions"]
    end

    Q --> Split["seed/dev/test manifest + checksums"]
    Split --> Test["held-out test loads only inside eval"]
    Test -. blocked from prompts/index/demo .-> Retriever
```

## 7. Modes and Pull-Ins

```mermaid
flowchart LR
    MVP["SHIPPED: text teach loop\nCLI + local Gradio"]
    MVP --> Quiz["SHIPPED PULL-IN: quiz mode"]
    Quiz --> SkillGap["SPEC ONLY: skill-gap diagnosis\ncited next-step plan"]
    SkillGap --> Interview["ROADMAP: mock interview\nopen answer -> cited grading -> follow-up -> report"]
    MVP --> Admin["Low-priority pull-in: admin upload"]
    MVP --> Voice["Pull-in: ElevenLabs voice"]
    MVP --> Memory["Later: cross-session memory"]

    style MVP fill:#EAFF00,stroke:#0F1419,stroke-width:2px
```

## 8. Deliverable Mapping

| Handout requirement | Architecture answer |
|---|---|
| Multi-step task | Teach loop from intake through report. |
| Tools | Retriever, Nebius item generation, grader, profile update, trace writer, escalation. |
| State | Within-session profile. |
| Human-in-the-loop | Refusal + review queue. |
| Tool failure / recovery | Retry, validation, fallback, confidence bands, escalation, stop guard. |
| How it worked | Held-out eval, trace, demo run, honest numbers. |
| Architecture diagram | Diagrams 1-7 in this file. |
