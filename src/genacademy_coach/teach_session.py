from __future__ import annotations

from typing import Any, Protocol

from pydantic import ValidationError

from genacademy_coach.escalation import append_review_queue
from genacademy_coach.grounding import (
    answer_grounded_in_spans,
)
from genacademy_coach.grounding import (
    grade_understanding as grade_answer_understanding,
)
from genacademy_coach.teach_agent import build_coach_agent
from genacademy_coach.teach_tools import TeachRuntime
from genacademy_coach.teach_types import (
    CoachAgentResponse,
    LearnerProfile,
    TeachSessionResult,
    TraceTurn,
)
from genacademy_coach.trace import TraceWriter

UNFAITHFUL_RESPONSE_REASON = "agent response was not faithful to retrieved citation text"
FALLBACK_STRATEGIES = ("contrastive_example", "step_by_step", "summary")


class AgentResponseError(RuntimeError):
    pass


class AgentPort(Protocol):
    def invoke(self, messages: list[dict[str, str]]) -> CoachAgentResponse: ...


class StaticAgentPort:
    def __init__(self, *responses: CoachAgentResponse):
        self._responses = list(responses)
        self._initial_count = len(self._responses)

    def invoke(self, messages: list[dict[str, str]]) -> CoachAgentResponse:
        if not self._responses:
            raise AgentResponseError(
                f"static agent responses exhausted after {self._initial_count} configured turns"
            )
        return self._responses.pop(0)


class LangChainAgentPort:
    def __init__(self, runtime: TeachRuntime, *, model: Any | None = None):
        self._agent = build_coach_agent(runtime, model=model)

    def invoke(self, messages: list[dict[str, str]]) -> CoachAgentResponse:
        result = self._agent.invoke({"messages": messages})
        structured = result.get("structured_response")
        if structured is None:
            raise AgentResponseError("missing structured_response")
        try:
            return CoachAgentResponse.model_validate(structured)
        except ValidationError as exc:
            raise AgentResponseError("invalid structured_response") from exc


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
    ):
        self.session_id = session_id
        self.topic = topic
        self.settings = settings
        self.foundation = foundation
        self.profile = profile
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
        return self._invoke_agent(f"Teach me this Gen Academy concept: {self.topic}")

    def respond(self, learner_answer: str) -> TeachSessionResult:
        self._grade_current_check_answer(learner_answer)
        return self._invoke_agent(f"Learner answer to current check: {learner_answer}")

    def _grade_current_check_answer(self, learner_answer: str) -> None:
        if self.runtime.current_check is None:
            return
        self.runtime.last_grade = grade_answer_understanding(
            learner_answer,
            self.runtime.current_check,
        )
        self.profile.last_grade_correct = self.runtime.last_grade.correct

    def _invoke_agent(self, learner_input: str) -> TeachSessionResult:
        if self.profile.turn_count >= self.settings.max_teach_turns:
            return self._write_result(
                learner_input,
                CoachAgentResponse(
                    learner_message="We have reached the turn limit for this teach loop.",
                    observation="turn budget reached before invoking the agent",
                    next_action="stop",
                    strategy="summary",
                    citation_ids=[],
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
        except AgentResponseError:
            if "retrieve_course_corpus" in self.runtime.tool_calls and not self.runtime.last_spans:
                response = self._refusal_response(
                    "no citeable course corpus found",
                    "I can't find this in the course materials, so I am escalating this "
                    "instead of guessing.",
                )
            else:
                response = self._refusal_response(
                    "agent failed to return structured output",
                    "I could not get a valid structured output from the tutor agent, so I am "
                    "escalating this instead of guessing.",
                )
        response = self._enforce_grounding(response, previous_strategy=previous_strategy)
        if response.next_action not in {"refuse_escalate", "stop"}:
            self.profile.previous_strategies.append(response.strategy)
        return self._write_result(learner_input, response)

    def _write_result(
        self,
        learner_input: str,
        response: CoachAgentResponse,
    ) -> TeachSessionResult:
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
                learner_input=learner_input,
                observation=response.observation,
                next_action=response.next_action,
                strategy=response.strategy,
                evidence_score=self.runtime.current_evidence_score(),
                evidence_band=self.runtime.current_evidence_band(),
                faithfulness_ok=faithfulness_ok,
                retrieved_citation_ids=[span.citation_id for span in self.runtime.last_spans],
                tool_calls=list(self.runtime.tool_calls),
                learner_message=response.learner_message,
            )
        )
        self.runtime.tool_calls.clear()
        self.runtime.escalation_queued = False
        return TeachSessionResult(
            session_id=self.session_id,
            profile=self.profile,
            response=response,
            trace_path=str(trace_path),
        )

    def _enforce_grounding(
        self,
        response: CoachAgentResponse,
        *,
        previous_strategy: str | None,
    ) -> CoachAgentResponse:
        # A wrong answer with citeable evidence must re-explain, even if the model tries to stop.
        if self._last_grade_is_incorrect() and self.runtime.last_spans:
            if (
                response.next_action != "re_explain_differently"
                or response.strategy == previous_strategy
            ):
                return self._grounded_reexplain_response(
                    previous_strategy=previous_strategy,
                    cited_spans=self.runtime.last_spans,
                )
        if (
            self._last_grade_is_correct()
            and self.runtime.last_spans
            and response.next_action in {"refuse_escalate", "stop"}
            and not self._citations_resolve(response)
        ):
            return self._grounded_advance_response(cited_spans=self.runtime.last_spans)
        if response.next_action in {"refuse_escalate", "stop"}:
            return response
        if (
            response.next_action == "re_explain_differently"
            and previous_strategy is not None
            and response.strategy == previous_strategy
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
        retrieved_by_id = {span.citation_id: span for span in self.runtime.last_spans}
        retrieved_ids = set(retrieved_by_id)
        if response.citation_ids and set(response.citation_ids).issubset(retrieved_ids):
            response = self._ensure_visible_citations(response)
            cited_spans = [retrieved_by_id[citation_id] for citation_id in response.citation_ids]
            if answer_grounded_in_spans(response.learner_message, cited_spans):
                return response
            if self._last_grade_is_incorrect():
                return self._grounded_reexplain_response(
                    previous_strategy=previous_strategy,
                    cited_spans=cited_spans,
                )
            if self._last_grade_is_correct():
                return self._grounded_advance_response(cited_spans=cited_spans)
            return self._refusal_response(
                UNFAITHFUL_RESPONSE_REASON,
                "I could not verify that answer against the retrieved course citation text, so "
                "I am escalating this to a mentor instead of guessing.",
                citation_ids=response.citation_ids,
            )
        if self._last_grade_is_incorrect() and self.runtime.last_spans:
            return self._grounded_reexplain_response(
                previous_strategy=previous_strategy,
                cited_spans=self.runtime.last_spans,
            )
        if self._last_grade_is_correct() and self.runtime.last_spans:
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

    def _last_grade_is_incorrect(self) -> bool:
        return self.runtime.last_grade is not None and not self.runtime.last_grade.correct

    def _last_grade_is_correct(self) -> bool:
        return self.runtime.last_grade is not None and self.runtime.last_grade.correct

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
        excerpt = " ".join(span.text.split())[:700].rstrip()
        return CoachAgentResponse(
            learner_message=f"{excerpt} [{span.citation_id}]",
            observation="grounded fallback after incorrect answer and unfaithful agent response",
            next_action="re_explain_differently",
            strategy=strategy,
            citation_ids=[span.citation_id],
            check_question=(
                self.runtime.current_check.question
                if self.runtime.current_check is not None
                else None
            ),
        )

    def _grounded_advance_response(
        self,
        *,
        cited_spans: list[Any],
    ) -> CoachAgentResponse:
        span = cited_spans[0]
        excerpt = " ".join(span.text.split())[:700].rstrip()
        return CoachAgentResponse(
            learner_message=f"{excerpt} [{span.citation_id}]",
            observation="grounded fallback after correct answer and unfaithful agent response",
            next_action="advance",
            strategy="summary",
            citation_ids=[span.citation_id],
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
                topic=self.topic,
                reason=reason,
                score=self.runtime.current_evidence_score(),
                citation_ids=cited,
            )
            self.runtime.escalation_queued = True
        return CoachAgentResponse(
            learner_message=learner_message,
            observation=reason,
            next_action="refuse_escalate",
            strategy="refusal",
            citation_ids=[],
        )
