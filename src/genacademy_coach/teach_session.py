from __future__ import annotations

import time
from typing import Any, Protocol

from pydantic import ValidationError

from genacademy_coach.escalation import append_review_queue
from genacademy_coach.grounding import (
    answer_grounded_in_spans,
)
from genacademy_coach.grounding import (
    grade_understanding as grade_answer_understanding,
)
from genacademy_coach.memory import NullEpisodicMemory, build_episodic_memory, seed_from_records
from genacademy_coach.memory_types import EpisodicMemory, EpisodicMemoryRecord
from genacademy_coach.privacy import learner_input_hash, topic_hash, topic_hash_or_existing
from genacademy_coach.teach_agent import build_coach_agent
from genacademy_coach.teach_tools import TeachRuntime
from genacademy_coach.teach_types import (
    CoachAgentResponse,
    DecisionSource,
    LearnerProfile,
    TeachSessionResult,
    TokenUsage,
    TraceTurn,
    UnderstandingGrade,
)
from genacademy_coach.trace import TraceWriter

UNFAITHFUL_RESPONSE_REASON = "agent response was not faithful to retrieved citation text"
STRUCTURED_OUTPUT_FAILURE_REASON = "agent failed to return structured output"
FALLBACK_STRATEGIES = ("contrastive_example", "step_by_step", "summary")
PYTHON_SAFETY_GATE_SOURCE: DecisionSource = "python safety gate"


def _grounded_excerpt(span: Any) -> str:
    return " ".join(span.text.split())[:700].rstrip()


def _with_decision_source(
    response: CoachAgentResponse,
    source: DecisionSource,
) -> CoachAgentResponse:
    response._decision_source = source
    return response


class AgentResponseError(RuntimeError):
    pass


def _sum_usage(messages: list[Any]) -> TokenUsage:
    usage = TokenUsage()
    for message in messages:
        metadata = getattr(message, "usage_metadata", None) or {}
        usage.input_tokens += int(metadata.get("input_tokens") or 0)
        usage.output_tokens += int(metadata.get("output_tokens") or 0)
        usage.total_tokens += int(metadata.get("total_tokens") or 0)
    return usage


def _add_usage(left: TokenUsage, right: TokenUsage) -> TokenUsage:
    return TokenUsage(
        input_tokens=left.input_tokens + right.input_tokens,
        output_tokens=left.output_tokens + right.output_tokens,
        total_tokens=left.total_tokens + right.total_tokens,
    )


class AgentPort(Protocol):
    last_usage: TokenUsage

    def invoke(self, messages: list[dict[str, str]]) -> CoachAgentResponse: ...


class StaticAgentPort:
    def __init__(self, *responses: CoachAgentResponse):
        self._responses = list(responses)
        self._initial_count = len(self._responses)
        self.last_usage = TokenUsage()

    def invoke(self, messages: list[dict[str, str]]) -> CoachAgentResponse:
        if not self._responses:
            raise AgentResponseError(
                f"static agent responses exhausted after {self._initial_count} configured turns"
            )
        return self._responses.pop(0)


class LangChainAgentPort:
    def __init__(self, runtime: TeachRuntime, *, model: Any | None = None):
        self._agent = build_coach_agent(runtime, model=model)
        self.last_usage = TokenUsage()

    def invoke(self, messages: list[dict[str, str]]) -> CoachAgentResponse:
        self.last_usage = TokenUsage()
        last_error: AgentResponseError | None = None
        for _attempt in range(2):
            result = self._agent.invoke({"messages": messages})
            self.last_usage = _add_usage(
                self.last_usage,
                _sum_usage(result.get("messages", [])),
            )
            structured = result.get("structured_response")
            if structured is None:
                last_error = AgentResponseError("missing structured_response")
                continue
            try:
                return CoachAgentResponse.model_validate(structured)
            except ValidationError as exc:
                last_error = AgentResponseError("invalid structured_response")
                last_error.__cause__ = exc
        if last_error is None:
            last_error = AgentResponseError("missing structured_response")
        raise last_error


class CoachSession:
    def __init__(
        self,
        *,
        session_id: str,
        topic: str,
        settings: Any,
        foundation: Any,
        profile: LearnerProfile,
        agent_port: AgentPort | None = None,
        memory: EpisodicMemory | None = None,
        user_id_hash: str | None = None,
    ):
        self.session_id = session_id
        self.topic = topic
        self.settings = settings
        self.foundation = foundation
        self.profile = profile
        self.user_id_hash = user_id_hash
        if memory is not None:
            self.memory = memory
        elif user_id_hash is not None:
            self.memory = build_episodic_memory(settings)
        else:
            self.memory = NullEpisodicMemory()
        self._memory_recalled = False
        self._memory_written = False
        self._last_response: CoachAgentResponse | None = None
        self._last_faithfulness_ok: bool | None = None
        self.runtime = TeachRuntime(
            session_id=session_id,
            topic=topic,
            profile=profile,
            foundation=foundation,
            stop_threshold=settings.stop_threshold,
            confirm_threshold=settings.confirm_threshold,
            review_queue_path=settings.review_queue_path,
        )
        self.agent_port = agent_port or LangChainAgentPort(self.runtime)
        self.trace_writer = TraceWriter(settings.trace_dir)

    def start(self) -> TeachSessionResult:
        self._recall_memory_once()
        return self._invoke_agent(f"Teach me this Gen Academy concept: {self.topic}")

    def respond(self, learner_answer: str) -> TeachSessionResult:
        self._grade_current_check_answer(learner_answer)
        answer_grade = self.runtime.last_grade if self.runtime.grade_locked else None
        return self._invoke_agent(
            f"Learner answer to current check: {learner_answer}",
            answer_grade=answer_grade,
        )

    def _grade_current_check_answer(self, learner_answer: str) -> None:
        self.runtime.grade_locked = False
        if self.runtime.current_check is None:
            return
        self.runtime.last_grade = grade_answer_understanding(
            learner_answer,
            self.runtime.current_check,
        )
        self.profile.last_grade_correct = self.runtime.last_grade.correct
        self.runtime.grade_locked = True

    def _invoke_agent(
        self,
        learner_input: str,
        *,
        answer_grade: UnderstandingGrade | None = None,
    ) -> TeachSessionResult:
        if self.profile.turn_count >= self.settings.max_teach_turns:
            return self._write_result(
                learner_input,
                _with_decision_source(
                    CoachAgentResponse(
                        learner_message="We have reached the turn limit for this teach loop.",
                        observation="turn budget reached before invoking the agent",
                        next_action="stop",
                        strategy="summary",
                        citation_ids=[],
                    ),
                    PYTHON_SAFETY_GATE_SOURCE,
                ),
            )

        previous_strategy = (
            self.profile.previous_strategies[-1] if self.profile.previous_strategies else None
        )
        self.profile.turn_count += 1
        current_check = (
            self.runtime.current_check.model_dump_json()
            if self.runtime.current_check is not None
            else "none"
        )
        last_grade = (
            self.runtime.last_grade.model_dump_json()
            if self.runtime.last_grade is not None
            else "none"
        )
        latency_ms = 0.0
        try:
            start = time.perf_counter()
            try:
                response = self.agent_port.invoke(
                    [
                        {
                            "role": "user",
                            "content": (
                                f"Session topic: {self.topic}\n"
                                f"Profile: {self.profile.model_dump_json()}\n"
                                f"Previous strategy: {previous_strategy}\n"
                                f"Current check: {current_check}\n"
                                f"Last grade: {last_grade}\n"
                                f"Learner input: {learner_input}"
                            ),
                        }
                    ]
                )
            finally:
                latency_ms = (time.perf_counter() - start) * 1000.0
                self.runtime.agent_latency_ms = latency_ms
        except AgentResponseError:
            if "retrieve_course_corpus" in self.runtime.tool_calls and not self.runtime.last_spans:
                response = self._refusal_response(
                    "no citeable course corpus found",
                    "I can't find this in the course materials, so I am escalating this "
                    "instead of guessing.",
                )
            else:
                response = self._refusal_response(
                    STRUCTURED_OUTPUT_FAILURE_REASON,
                    "I could not get a valid structured output from the tutor agent, so I am "
                    "escalating this instead of guessing.",
                )
        response = self._enforce_grounding(
            response,
            previous_strategy=previous_strategy,
            answer_grade=answer_grade,
        )
        if answer_grade is not None:
            self.runtime.last_grade = answer_grade
            self.profile.last_grade_correct = answer_grade.correct
        if response.next_action not in {"refuse_escalate", "stop"}:
            self.profile.previous_strategies.append(response.strategy)
        usage = getattr(self.agent_port, "last_usage", None) or TokenUsage()
        return self._write_result(
            learner_input,
            response,
            latency_ms=latency_ms,
            usage=usage,
        )

    def _write_result(
        self,
        learner_input: str,
        response: CoachAgentResponse,
        *,
        latency_ms: float = 0.0,
        usage: TokenUsage | None = None,
    ) -> TeachSessionResult:
        usage = usage or TokenUsage()
        cited_spans = [
            span for span in self.runtime.last_spans if span.citation_id in response.citation_ids
        ]
        faithfulness_ok = (
            False
            if response.observation == UNFAITHFUL_RESPONSE_REASON
            else (
                None
                if response.next_action in {"refuse_escalate", "stop"} or not cited_spans
                else answer_grounded_in_spans(response.learner_message, cited_spans)
            )
        )
        trace_path = self.trace_writer.append(
            TraceTurn(
                session_id=self.session_id,
                turn=self.profile.turn_count,
                topic_hash=topic_hash(self.topic),
                learner_input_hash=learner_input_hash(learner_input),
                next_action=response.next_action,
                strategy=response.strategy,
                evidence_score=self.runtime.current_evidence_score(),
                evidence_band=self.runtime.current_evidence_band(),
                faithfulness_ok=faithfulness_ok,
                retrieved_citation_ids=[span.citation_id for span in self.runtime.last_spans],
                retrieved_citation_labels=[span.source_label for span in self.runtime.last_spans],
                tool_calls=list(self.runtime.tool_calls),
                tool_latencies_ms=dict(self.runtime.tool_latencies_ms),
                tool_call_counts=dict(self.runtime.tool_call_counts),
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
                latency_ms=latency_ms,
                agent_latency_ms=self.runtime.agent_latency_ms,
            )
        )
        self._last_response = response
        self._last_faithfulness_ok = faithfulness_ok
        self.runtime.reset_turn_observability()
        self.runtime.escalation_queued = False
        self.runtime.grade_locked = False
        return TeachSessionResult(
            session_id=self.session_id,
            profile=self.profile,
            response=response,
            trace_path=str(trace_path),
        )

    def finish(self) -> None:
        if not self._should_write_memory():
            return
        assert self.user_id_hash is not None
        assert self._last_response is not None
        self.memory.write(
            user_id_hash=self.user_id_hash,
            record=self._memory_record_from_profile(self._last_response),
        )
        self._memory_written = True

    def _recall_memory_once(self) -> None:
        if self._memory_recalled:
            return
        self._memory_recalled = True
        if self.user_id_hash is None:
            return
        records = self.memory.recall(
            user_id_hash=self.user_id_hash,
            topic_hash=topic_hash(self.topic),
        )
        if not records:
            return
        seed = seed_from_records(records)
        if seed.style is not None:
            self.profile.style = seed.style
        if seed.track_lens is not None:
            self.profile.track_lens = seed.track_lens
        self.profile.known = sorted(set([*self.profile.known, *seed.known_topic_hashes]))
        self.profile.struggled = sorted(
            set([*self.profile.struggled, *seed.struggled_topic_hashes])
        )

    def _should_write_memory(self) -> bool:
        if self._memory_written or self.user_id_hash is None or self._last_response is None:
            return False
        if self._last_response.next_action in {"refuse_escalate", "stop"}:
            return False
        if self.runtime.current_evidence_band() == "stop":
            return False
        if not self.runtime.last_spans:
            return False
        return self._last_faithfulness_ok is not False

    def _memory_record_from_profile(
        self,
        response: CoachAgentResponse,
    ) -> EpisodicMemoryRecord:
        active_topic_hash = topic_hash(self.topic)
        known = {topic_hash_or_existing(item) for item in self.profile.known}
        struggled = {topic_hash_or_existing(item) for item in self.profile.struggled}
        if self.profile.last_grade_correct is True or response.next_action == "advance":
            known.add(active_topic_hash)
        if self.profile.last_grade_correct is False or response.next_action in {
            "drill",
            "re_explain_differently",
        }:
            struggled.add(active_topic_hash)
        return EpisodicMemoryRecord(
            topic_hash=active_topic_hash,
            source_session_id=self.session_id,
            style=self.profile.style,
            track_lens=self.profile.track_lens,
            known_topic_hashes=sorted(known),
            struggled_topic_hashes=sorted(struggled),
            session_count=1,
            turn_count=self.profile.turn_count,
        )

    def _enforce_grounding(
        self,
        response: CoachAgentResponse,
        *,
        previous_strategy: str | None,
        answer_grade: UnderstandingGrade | None = None,
    ) -> CoachAgentResponse:
        # A wrong answer with citeable evidence must re-explain, even if the model tries to stop.
        if self._last_grade_is_incorrect(answer_grade) and self.runtime.last_spans:
            if (
                response.next_action != "re_explain_differently"
                or response.strategy == previous_strategy
            ):
                return self._grounded_reexplain_response(
                    previous_strategy=previous_strategy,
                    cited_spans=self.runtime.last_spans,
                )
        retrieved_by_id = {span.citation_id: span for span in self.runtime.last_spans}
        if (
            self._last_grade_is_correct(answer_grade)
            and self.runtime.last_spans
            and response.next_action in {"refuse_escalate", "stop"}
        ):
            if response.citation_ids and set(response.citation_ids).issubset(
                retrieved_by_id
            ):
                return self._grounded_advance_response(
                    cited_spans=[
                        retrieved_by_id[citation_id]
                        for citation_id in response.citation_ids
                    ]
                )
            return self._grounded_advance_response(cited_spans=self.runtime.last_spans)
        if response.next_action in {"refuse_escalate", "stop"}:
            return response
        if (
            response.next_action == "re_explain_differently"
            and previous_strategy is not None
            and response.strategy == previous_strategy
            and not self._last_grade_is_correct(answer_grade)
        ):
            return self._refusal_response(
                "agent chose re_explain_differently without changing strategy",
                "I could not produce a different strategy for the re-explanation, so I am "
                "escalating this instead of repeating the same approach.",
            )
        if self.runtime.current_check is not None:
            response = response.model_copy(
                update={"check_question": self.runtime.current_check.question}
            )
        elif response.check_question is not None:
            return self._refusal_response(
                "agent displayed a check question that was not generated by the grounded tool",
                "I could not verify the check question against a retrieved course span, so I am "
                "escalating this instead of asking it.",
            )
        retrieved_ids = set(retrieved_by_id)
        if response.citation_ids and set(response.citation_ids).issubset(retrieved_ids):
            response = self._ensure_visible_citations(response)
            cited_spans = [retrieved_by_id[citation_id] for citation_id in response.citation_ids]
            if (
                self._last_grade_is_correct(answer_grade)
                and response.next_action in {"drill", "re_explain_differently"}
            ):
                return self._grounded_advance_response(cited_spans=cited_spans)
            if answer_grounded_in_spans(response.learner_message, cited_spans):
                return response
            if self._last_grade_is_incorrect(answer_grade):
                return self._grounded_reexplain_response(
                    previous_strategy=previous_strategy,
                    cited_spans=cited_spans,
                )
            if self._last_grade_is_correct(answer_grade):
                return self._grounded_advance_response(cited_spans=cited_spans)
            if (
                self.runtime.current_check is not None
                and response.next_action in {"advance", "drill"}
            ):
                check_span = retrieved_by_id.get(self.runtime.current_check.citation_id)
                if check_span is None:
                    return self._refusal_response(
                        "grounded check citation was not present in retrieved spans",
                        "I could not verify the check question against a retrieved course "
                        "citation, so I am escalating this instead of asking it.",
                        citation_ids=response.citation_ids,
                    )
                return self._grounded_teach_response(
                    response=response,
                    cited_span=check_span,
                )
            return self._refusal_response(
                UNFAITHFUL_RESPONSE_REASON,
                "I could not verify that answer against the retrieved course citation text, so "
                "I am escalating this to a mentor instead of guessing.",
                citation_ids=response.citation_ids,
            )
        if self._last_grade_is_incorrect(answer_grade) and self.runtime.last_spans:
            return self._grounded_reexplain_response(
                previous_strategy=previous_strategy,
                cited_spans=self.runtime.last_spans,
            )
        if self._last_grade_is_correct(answer_grade) and self.runtime.last_spans:
            return self._grounded_advance_response(cited_spans=self.runtime.last_spans)
        return self._refusal_response(
            "agent response had no retrieved citation_ids",
            "I could not verify that answer against a retrieved course citation, so I am "
            "escalating this to a mentor instead of guessing.",
            citation_ids=response.citation_ids,
        )

    def _ensure_visible_citations(self, response: CoachAgentResponse) -> CoachAgentResponse:
        missing = [
            citation_id
            for citation_id in response.citation_ids
            if f"[{citation_id}]" not in response.learner_message
        ]
        if not missing:
            return response
        learner_message = response.learner_message.rstrip() + " " + " ".join(
            f"[{citation_id}]" for citation_id in missing
        )
        return response.model_copy(update={"learner_message": learner_message})

    def _citations_resolve(self, response: CoachAgentResponse) -> bool:
        retrieved_ids = {span.citation_id for span in self.runtime.last_spans}
        return bool(response.citation_ids) and set(response.citation_ids).issubset(
            retrieved_ids
        )

    def _effective_grade(
        self,
        answer_grade: UnderstandingGrade | None = None,
    ) -> UnderstandingGrade | None:
        return answer_grade if answer_grade is not None else self.runtime.last_grade

    def _last_grade_is_incorrect(
        self,
        answer_grade: UnderstandingGrade | None = None,
    ) -> bool:
        grade = self._effective_grade(answer_grade)
        return grade is not None and not grade.correct

    def _last_grade_is_correct(
        self,
        answer_grade: UnderstandingGrade | None = None,
    ) -> bool:
        grade = self._effective_grade(answer_grade)
        return grade is not None and grade.correct

    def _grounded_reexplain_response(
        self,
        *,
        previous_strategy: str | None,
        cited_spans: list[Any],
    ) -> CoachAgentResponse:
        span = cited_spans[0]
        strategy = next(
            item for item in FALLBACK_STRATEGIES if item != previous_strategy
        )
        excerpt = _grounded_excerpt(span)
        return _with_decision_source(
            CoachAgentResponse(
                learner_message=f"{excerpt} [{span.citation_id}]",
                observation=(
                    "grounded fallback after incorrect answer and unfaithful agent response"
                ),
                next_action="re_explain_differently",
                strategy=strategy,
                citation_ids=[span.citation_id],
                check_question=(
                    self.runtime.current_check.question
                    if self.runtime.current_check is not None
                    else None
                ),
            ),
            PYTHON_SAFETY_GATE_SOURCE,
        )

    def _grounded_advance_response(
        self,
        *,
        cited_spans: list[Any],
    ) -> CoachAgentResponse:
        span = cited_spans[0]
        excerpt = _grounded_excerpt(span)
        return _with_decision_source(
            CoachAgentResponse(
                learner_message=f"{excerpt} [{span.citation_id}]",
                observation="grounded fallback after correct answer and unfaithful agent response",
                next_action="advance",
                strategy="summary",
                citation_ids=[span.citation_id],
            ),
            PYTHON_SAFETY_GATE_SOURCE,
        )

    def _grounded_teach_response(
        self,
        *,
        response: CoachAgentResponse,
        cited_span: Any,
    ) -> CoachAgentResponse:
        excerpt = _grounded_excerpt(cited_span)
        return _with_decision_source(
            CoachAgentResponse(
                learner_message=f"{excerpt} [{cited_span.citation_id}]",
                observation="grounded fallback after initial unfaithful agent response",
                next_action=response.next_action,
                strategy=response.strategy,
                citation_ids=[cited_span.citation_id],
                check_question=(
                    self.runtime.current_check.question
                    if self.runtime.current_check is not None
                    else None
                ),
            ),
            PYTHON_SAFETY_GATE_SOURCE,
        )

    def _refusal_response(
        self,
        reason: str,
        learner_message: str,
        *,
        citation_ids: list[str] | None = None,
    ) -> CoachAgentResponse:
        cited = citation_ids or []
        if not self.runtime.escalation_queued:
            append_review_queue(
                self.settings.review_queue_path,
                session_id=self.session_id,
                topic_hash=topic_hash(self.topic),
                reason=reason,
                score=self.runtime.current_evidence_score(),
                citation_ids=cited,
            )
            self.runtime.escalation_queued = True
        return _with_decision_source(
            CoachAgentResponse(
                learner_message=learner_message,
                observation=reason,
                next_action="refuse_escalate",
                strategy="refusal",
                citation_ids=[],
            ),
            PYTHON_SAFETY_GATE_SOURCE,
        )
